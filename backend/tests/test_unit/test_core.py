"""
Unit tests for core modules — Sprint 01 scope.
"""

import pytest
from core.exceptions import AuthenticationError, UTOSException, ValidationError
from core.security import PasswordManager, TokenManager


class TestExceptions:
    """Test custom exceptions — Sprint 01."""

    def test_utos_exception(self):
        exc = UTOSException(
            message="Test error", error_code="TEST_ERROR", details={"k": "v"}
        )
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {"k": "v"}
        assert str(exc) == "Test error"

    def test_validation_error_is_utos_exception(self):
        exc = ValidationError("Invalid input")
        assert isinstance(exc, UTOSException)
        assert exc.message == "Invalid input"

    def test_authentication_error_is_utos_exception(self):
        exc = AuthenticationError("Invalid credentials")
        assert isinstance(exc, UTOSException)
        assert exc.message == "Invalid credentials"


class TestPasswordManager:
    """Test PasswordManager utilities."""

    def setup_method(self):
        self.pm = PasswordManager()

    def test_hash_password_produces_bcrypt_hash(self):
        hashed = self.pm.hash_password("TestPassword123!")
        assert hashed != "TestPassword123!"
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = self.pm.hash_password("TestPassword123!")
        assert self.pm.verify_password("TestPassword123!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = self.pm.hash_password("TestPassword123!")
        assert self.pm.verify_password("WrongPassword!", hashed) is False


class TestTokenManager:
    """Test JWT TokenManager."""

    def setup_method(self):
        self.tm = TokenManager()

    def test_create_and_verify_access_token(self):
        token = self.tm.create_access_token({"sub": "user-123", "email": "a@b.com"})
        assert isinstance(token, str)
        payload = self.tm.verify_token(token, token_type="access")
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_create_and_verify_refresh_token(self):
        token = self.tm.create_refresh_token({"sub": "user-123"})
        payload = self.tm.verify_token(token, token_type="refresh")
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_expired_token_raises_authentication_error(self):
        from datetime import timedelta

        token = self.tm.create_access_token(
            {"sub": "x"}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(AuthenticationError):
            self.tm.verify_token(token)

    def test_wrong_token_type_raises_authentication_error(self):
        token = self.tm.create_access_token({"sub": "x"})
        with pytest.raises(AuthenticationError):
            self.tm.verify_token(token, token_type="refresh")
