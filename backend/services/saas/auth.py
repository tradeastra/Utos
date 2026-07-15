"""
AuthService — authentication service wrapping PasswordManager and TokenManager.

Provides register, login, refresh, password reset, MFA stub, and session management.
Does NOT import engine modules (Architecture Freeze).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from core.config import settings
from core.exceptions import AuthenticationError, ValidationError
from core.logging import get_logger
from core.security import PasswordManager, TokenManager

logger = get_logger(__name__)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


@dataclass
class MFAState:
    enabled: bool = False
    secret: str | None = None
    verified: bool = False


class AuthService:
    """Authentication service — wraps security utilities with business logic."""

    def __init__(
        self,
        user_repo: Any | None = None,
        password_manager: PasswordManager | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._password = password_manager or PasswordManager()
        self._token = token_manager or TokenManager()
        self._mfa_states: dict[str, MFAState] = {}
        self._metrics: dict[str, int] = {
            "registrations": 0,
            "logins": 0,
            "token_refreshes": 0,
            "password_resets": 0,
            "mfa_enables": 0,
        }

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> dict[str, Any]:
        if not email or "@" not in email:
            raise ValidationError("Invalid email address")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        if self._user_repo is not None:
            if await self._user_repo.exists_by_email(email):
                raise AuthenticationError("Email already registered")
            hashed = self._password.hash_password(password)
            user = await self._user_repo.create(
                email=email.lower(),
                password_hash=hashed,
                full_name=full_name,
            )
            self._metrics["registrations"] += 1
            logger.info("User registered", extra={"user_id": str(user.id)})
            return {"id": str(user.id), "email": user.email, "full_name": user.full_name}

        self._metrics["registrations"] += 1
        return {"id": str(uuid.uuid4()), "email": email.lower(), "full_name": full_name}

    async def login(self, email: str, password: str) -> TokenPair:
        if self._user_repo is not None:
            user = await self._user_repo.get_by_email(email)
            if user is None:
                raise AuthenticationError("Invalid credentials")
            if not self._password.verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid credentials")
            if not user.is_active:
                raise AuthenticationError("Account is disabled")
            payload = {"sub": str(user.id), "email": user.email}
        else:
            payload = {"sub": str(uuid.uuid4()), "email": email}

        access = self._token.create_access_token(payload)
        refresh = self._token.create_refresh_token(payload)
        self._metrics["logins"] += 1
        logger.info("User logged in", extra={"email": email})
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_token(self, refresh_token: str) -> str:
        payload = self._token.verify_token(refresh_token, token_type="refresh")
        new_access = self._token.create_access_token(
            {"sub": payload["sub"], "email": payload.get("email")}
        )
        self._metrics["token_refreshes"] += 1
        return new_access

    async def verify_email(self, token: str) -> bool:
        try:
            email = self._token.verify_email_token(token)
            logger.info("Email verified", extra={"email": email})
            return True
        except AuthenticationError:
            return False

    async def request_password_reset(self, email: str) -> str:
        token = self._token.create_password_reset_token(email)
        logger.info("Password reset requested", extra={"email": email})
        return token

    async def reset_password(self, token: str, new_password: str) -> bool:
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        try:
            email = self._token.verify_password_reset_token(token)
        except AuthenticationError:
            return False

        if self._user_repo is not None:
            user = await self._user_repo.get_by_email(email)
            if user is None:
                return False
            hashed = self._password.hash_password(new_password)
            await self._user_repo.update(user, password_hash=hashed)

        self._metrics["password_resets"] += 1
        logger.info("Password reset", extra={"email": email})
        return True

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        if self._user_repo is not None:
            user = await self._user_repo.get_by_id(uuid.UUID(user_id))
            if user is None:
                return False
            if not self._password.verify_password(old_password, user.password_hash):
                return False
            hashed = self._password.hash_password(new_password)
            await self._user_repo.update(user, password_hash=hashed)

        logger.info("Password changed", extra={"user_id": user_id})
        return True

    async def enable_mfa(self, user_id: str) -> str:
        import secrets as _secrets
        secret = _secrets.token_hex(20)
        self._mfa_states[user_id] = MFAState(enabled=True, secret=secret, verified=False)
        self._metrics["mfa_enables"] += 1
        logger.info("MFA enabled", extra={"user_id": user_id})
        return secret

    async def verify_mfa(self, user_id: str, code: str) -> bool:
        state = self._mfa_states.get(user_id)
        if state is None or not state.enabled:
            return False
        if len(code) != 6:
            return False
        state.verified = True
        return True

    async def disable_mfa(self, user_id: str) -> bool:
        if user_id in self._mfa_states:
            del self._mfa_states[user_id]
            logger.info("MFA disabled", extra={"user_id": user_id})
            return True
        return False

    def get_mfa_state(self, user_id: str) -> MFAState | None:
        return self._mfa_states.get(user_id)

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
