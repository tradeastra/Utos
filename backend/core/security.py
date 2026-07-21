"""
Security utilities for UTOS Trading Engine.

This module provides password hashing, JWT token management, and
other security-related utilities.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt
from core.config import settings
from core.exceptions import AuthenticationError
from core.logging import get_logger

logger = get_logger(__name__)


class PasswordManager:
    """Password hashing and verification utilities."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        try:
            encoded = password.encode("utf-8")
            return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise AuthenticationError("Failed to hash password")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            encoded = plain_password.encode("utf-8")
            encoded_hash = hashed_password.encode("utf-8")
            return bcrypt.checkpw(encoded, encoded_hash)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    @staticmethod
    def generate_password(length: int = 12) -> str:
        """Generate a secure random password."""
        try:
            alphabet = (
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            )
            return "".join(secrets.choice(alphabet) for _ in range(length))
        except Exception as e:
            logger.error(f"Password generation error: {e}")
            raise AuthenticationError("Failed to generate password")


class TokenManager:
    """JWT token management utilities."""

    @staticmethod
    def create_access_token(
        data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT access token."""
        try:
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )

            import secrets as _secrets
            to_encode.update(
                {"exp": expire, "iat": datetime.utcnow(), "type": "access", "jti": _secrets.token_urlsafe(16)}
            )

            encoded_jwt = jwt.encode(
                to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )

            return encoded_jwt

        except Exception as e:
            logger.error(f"Access token creation error: {e}")
            raise AuthenticationError("Failed to create access token")

    @staticmethod
    def create_refresh_token(
        data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT refresh token."""
        try:
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    days=settings.REFRESH_TOKEN_EXPIRE_DAYS
                )

            to_encode.update(
                {"exp": expire, "iat": datetime.utcnow(), "type": "refresh"}
            )

            encoded_jwt = jwt.encode(
                to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )

            return encoded_jwt

        except Exception as e:
            logger.error(f"Refresh token creation error: {e}")
            raise AuthenticationError("Failed to create refresh token")

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )

            # Check token type
            if payload.get("type") != token_type:
                raise AuthenticationError(f"Invalid token type: expected {token_type}")

            # Check expiration
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
                raise AuthenticationError("Token has expired")

            # Check blocklist (only for access tokens)
            if token_type == "access":
                jti = payload.get("jti")
                if jti and TokenManager.is_token_blacklisted(jti):
                    raise AuthenticationError("Token has been revoked")

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Token verification error: {e}")
            raise AuthenticationError("Invalid token")
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise AuthenticationError("Failed to verify token")

    @staticmethod
    def is_token_blacklisted(jti: str) -> bool:
        """Check if a token's jti is in the Redis blocklist."""
        try:
            from database.redis_client import get_redis

            redis = get_redis()
            if redis is None:
                return False
            return bool(redis.exists(f"token_blocklist:{jti}"))
        except Exception:
            return False

    @staticmethod
    async def revoke_token(token: str) -> None:
        """Add a token to the Redis blocklist with TTL matching its expiry."""
        try:
            from database.redis_client import get_redis

            redis = get_redis()
            if redis is None:
                return

            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            jti = payload.get("jti")
            exp = payload.get("exp")
            if not jti or not exp:
                return

            import time as _time
            ttl = int(exp - _time.time())
            if ttl > 0:
                await redis.set(f"token_blocklist:{jti}", "1", ex=ttl)
        except Exception as e:
            logger.error(f"Token revocation error: {e}")

    @staticmethod
    def create_email_verification_token(email: str) -> str:
        """Create an email verification token."""
        try:
            to_encode = {
                "email": email,
                "type": "email_verification",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=24),
            }

            return jwt.encode(
                to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )

        except Exception as e:
            logger.error(f"Email verification token creation error: {e}")
            raise AuthenticationError("Failed to create email verification token")

    @staticmethod
    def verify_email_token(token: str) -> str:
        """Verify an email verification token and return email."""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )

            if payload.get("type") != "email_verification":
                raise AuthenticationError("Invalid token type")

            email = payload.get("email")
            if not email:
                raise AuthenticationError("Invalid token payload")

            return email

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Email verification token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Email token verification error: {e}")
            raise AuthenticationError("Invalid email verification token")
        except Exception as e:
            logger.error(f"Email token verification error: {e}")
            raise AuthenticationError("Failed to verify email token")

    @staticmethod
    def create_password_reset_token(email: str) -> str:
        """Create a password reset token."""
        try:
            to_encode = {
                "email": email,
                "type": "password_reset",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=1),
            }

            return jwt.encode(
                to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )

        except Exception as e:
            logger.error(f"Password reset token creation error: {e}")
            raise AuthenticationError("Failed to create password reset token")

    @staticmethod
    def verify_password_reset_token(token: str) -> str:
        """Verify a password reset token and return email."""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )

            if payload.get("type") != "password_reset":
                raise AuthenticationError("Invalid token type")

            email = payload.get("email")
            if not email:
                raise AuthenticationError("Invalid token payload")

            return email

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Password reset token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Password reset token verification error: {e}")
            raise AuthenticationError("Invalid password reset token")
        except Exception as e:
            logger.error(f"Password reset token verification error: {e}")
            raise AuthenticationError("Failed to verify password reset token")


class APIKeyManager:
    """API key management utilities."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        try:
            return secrets.token_urlsafe(32)
        except Exception as e:
            logger.error(f"API key generation error: {e}")
            raise AuthenticationError("Failed to generate API key")

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage."""
        try:
            encoded = api_key.encode("utf-8")
            return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")
        except Exception as e:
            logger.error(f"API key hashing error: {e}")
            raise AuthenticationError("Failed to hash API key")

    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        try:
            encoded = api_key.encode("utf-8")
            encoded_hash = hashed_key.encode("utf-8")
            return bcrypt.checkpw(encoded, encoded_hash)
        except Exception as e:
            logger.error(f"API key verification error: {e}")
            return False


class SecurityUtils:
    """General security utilities."""

    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure session ID."""
        try:
            return secrets.token_urlsafe(32)
        except Exception as e:
            logger.error(f"Session ID generation error: {e}")
            raise AuthenticationError("Failed to generate session ID")

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a CSRF token."""
        try:
            return secrets.token_urlsafe(32)
        except Exception as e:
            logger.error(f"CSRF token generation error: {e}")
            raise AuthenticationError("Failed to generate CSRF token")

    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """Sanitize user input to prevent XSS."""
        try:
            # Basic XSS prevention
            dangerous_chars = ["<", ">", "&", '"', "'", "/"]
            sanitized = input_string

            for char in dangerous_chars:
                sanitized = sanitized.replace(char, "")

            return sanitized
        except Exception as e:
            logger.error(f"Input sanitization error: {e}")
            return input_string

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        try:
            import re

            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return re.match(pattern, email) is not None
        except Exception as e:
            logger.error(f"Email validation error: {e}")
            return False

    @staticmethod
    def validate_password_strength(password: str) -> dict[str, Any]:
        """Validate password strength."""
        try:
            result: dict[str, Any] = {"is_valid": True, "errors": [], "score": 0}

            # Length check
            if len(password) < 8:
                result["is_valid"] = False
                result["errors"].append("Password must be at least 8 characters long")
            else:
                result["score"] += 1

            # Uppercase check
            if not any(c.isupper() for c in password):
                result["is_valid"] = False
                result["errors"].append(
                    "Password must contain at least one uppercase letter"
                )
            else:
                result["score"] += 1

            # Lowercase check
            if not any(c.islower() for c in password):
                result["is_valid"] = False
                result["errors"].append(
                    "Password must contain at least one lowercase letter"
                )
            else:
                result["score"] += 1

            # Number check
            if not any(c.isdigit() for c in password):
                result["is_valid"] = False
                result["errors"].append("Password must contain at least one number")
            else:
                result["score"] += 1

            # Special character check
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                result["is_valid"] = False
                result["errors"].append(
                    "Password must contain at least one special character"
                )
            else:
                result["score"] += 1

            return result

        except Exception as e:
            logger.error(f"Password strength validation error: {e}")
            return {"is_valid": False, "errors": ["Validation error"], "score": 0}


# Create instances
password_manager = PasswordManager()
token_manager = TokenManager()
api_key_manager = APIKeyManager()
security_utils = SecurityUtils()
