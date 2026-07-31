"""
Credential manager for secure API key encryption / decryption — Sprint 3.

Uses Fernet (AES-128-CBC with HMAC) with a key derived from the
application's secret key. The encrypted values are stored in the database;
plaintext keys never persist.
"""

import base64
import os

from core.config import settings
from core.exceptions import AuthenticationError
from core.logging import get_logger
from cryptography.fernet import Fernet, InvalidToken

logger = get_logger(__name__)


class CredentialManager:
    """Encrypt and decrypt exchange API credentials."""

    def __init__(self, secret_key: str | None = None) -> None:
        """Initialize with a secret key; defaults to `settings.SECRET_KEY`."""
        self._cipher = self._make_fernet(secret_key)

    @staticmethod
    def _make_fernet(secret_key: str | None = None) -> Fernet:
        """Derive a Fernet key using the same method as exchange_accounts._get_fernet()."""
        key = os.environ.get("ENCRYPTION_KEY", "")
        if not key:
            raw = (secret_key or settings.SECRET_KEY).encode("utf-8")[:32]
            key = base64.urlsafe_b64encode(raw.ljust(32, b"0")).decode()
        else:
            key = key if isinstance(key, str) else key.decode()
        return Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return a base64-encoded token."""
        try:
            token = self._cipher.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as e:
            logger.error(f"Credential encryption error: {e}")
            raise AuthenticationError("Failed to encrypt credential") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted token back to plaintext."""
        try:
            token = ciphertext.encode("utf-8")
            return self._cipher.decrypt(token).decode("utf-8")
        except InvalidToken as e:
            logger.error("Credential decryption failed: invalid token")
            raise AuthenticationError("Invalid credential token") from e
        except Exception as e:
            logger.error(f"Credential decryption error: {e}")
            raise AuthenticationError("Failed to decrypt credential") from e

    def mask(self, value: str, visible: int = 4) -> str:
        """Mask a secret value, leaving only the last `visible` chars readable."""
        if visible <= 0:
            return "*" * len(value)
        if visible >= len(value):
            return value
        return "*" * (len(value) - visible) + value[-visible:]
