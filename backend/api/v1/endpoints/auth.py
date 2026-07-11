"""
Authentication endpoints — register, login, refresh, logout.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import AuthenticationError
from core.logging import get_logger
from core.security import PasswordManager, TokenManager
from database.base import get_db
from repositories.user_repository import UserRepository
from schemas.auth import (
    AccessTokenResponse,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter()
logger = get_logger(__name__)
_bearer = HTTPBearer()

password_manager = PasswordManager()
token_manager = TokenManager()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new user account."""
    repo = UserRepository(db)
    if await repo.exists_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "EMAIL_EXISTS",
                    "message": "Email already registered",
                    "details": None,
                }
            },
        )
    hashed = password_manager.hash_password(body.password)
    user = await repo.create(email=body.email, password_hash=hashed, full_name=body.full_name)
    logger.info("User registered", extra={"user_id": str(user.id)})
    return {
        "data": UserResponse.model_validate(user).model_dump(),
        "meta": {"timestamp": _now_iso()},
    }


@router.post("/login", response_model=dict)
async def login(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticate and return JWT tokens."""
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not password_manager.verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                    "details": None,
                }
            },
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "ACCOUNT_DISABLED", "message": "Account is disabled", "details": None}},
        )
    payload = {"sub": str(user.id), "email": user.email}
    access_token = token_manager.create_access_token(payload)
    refresh_token = token_manager.create_refresh_token(payload)
    logger.info("User logged in", extra={"user_id": str(user.id)})
    return {
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        "meta": {"timestamp": _now_iso()},
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(body: RefreshTokenRequest) -> dict:
    """Return a new access token given a valid refresh token."""
    try:
        payload = token_manager.verify_token(body.refresh_token, token_type="refresh")
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": str(exc), "details": None}},
        ) from exc
    new_token = token_manager.create_access_token(
        {"sub": payload["sub"], "email": payload.get("email")}
    )
    return {
        "data": {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        "meta": {"timestamp": _now_iso()},
    }


@router.post("/logout", response_model=dict)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    """Invalidate the current session.

    Note: token blocklist not implemented in Sprint 01 — the token expires
    naturally after ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    logger.info("User logged out")
    return {
        "data": {"message": "Successfully logged out"},
        "meta": {"timestamp": _now_iso()},
    }
