"""Unit tests for AuthService."""

import pytest

from core.exceptions import AuthenticationError, ValidationError
from services.saas.auth import AuthService, TokenPair


class TestRegister:

    @pytest.mark.asyncio
    async def test_register_success(self) -> None:
        svc = AuthService()
        result = await svc.register("user@example.com", "SecurePass1!", "Test User")
        assert result["email"] == "user@example.com"
        assert result["full_name"] == "Test User"
        assert "id" in result
        assert svc.get_metrics()["registrations"] == 1

    @pytest.mark.asyncio
    async def test_register_invalid_email(self) -> None:
        svc = AuthService()
        with pytest.raises(ValidationError):
            await svc.register("not-an-email", "SecurePass1!")

    @pytest.mark.asyncio
    async def test_register_short_password(self) -> None:
        svc = AuthService()
        with pytest.raises(ValidationError):
            await svc.register("user@example.com", "short")


class TestLogin:

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        svc = AuthService()
        tokens = await svc.login("user@example.com", "password")
        assert isinstance(tokens, TokenPair)
        assert tokens.token_type == "bearer"
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0
        assert svc.get_metrics()["logins"] == 1


class TestRefresh:

    @pytest.mark.asyncio
    async def test_refresh_token(self) -> None:
        svc = AuthService()
        tokens = await svc.login("user@example.com", "password")
        new_access = await svc.refresh_token(tokens.refresh_token)
        assert isinstance(new_access, str)
        assert len(new_access) > 0
        assert svc.get_metrics()["token_refreshes"] == 1


class TestPasswordReset:

    @pytest.mark.asyncio
    async def test_request_and_reset(self) -> None:
        svc = AuthService()
        token = await svc.request_password_reset("user@example.com")
        assert isinstance(token, str)
        result = await svc.reset_password(token, "NewSecurePass1!")
        assert result is True
        assert svc.get_metrics()["password_resets"] == 1

    @pytest.mark.asyncio
    async def test_reset_short_password(self) -> None:
        svc = AuthService()
        token = await svc.request_password_reset("user@example.com")
        with pytest.raises(ValidationError):
            await svc.reset_password(token, "short")


class TestMFA:

    @pytest.mark.asyncio
    async def test_enable_mfa(self) -> None:
        svc = AuthService()
        secret = await svc.enable_mfa("user-1")
        assert isinstance(secret, str)
        assert len(secret) > 0
        assert svc.get_mfa_state("user-1").enabled is True

    @pytest.mark.asyncio
    async def test_verify_mfa(self) -> None:
        svc = AuthService()
        await svc.enable_mfa("user-1")
        assert await svc.verify_mfa("user-1", "123456") is True
        assert svc.get_mfa_state("user-1").verified is True

    @pytest.mark.asyncio
    async def test_verify_mfa_wrong_length(self) -> None:
        svc = AuthService()
        await svc.enable_mfa("user-1")
        assert await svc.verify_mfa("user-1", "123") is False

    @pytest.mark.asyncio
    async def test_verify_mfa_not_enabled(self) -> None:
        svc = AuthService()
        assert await svc.verify_mfa("user-1", "123456") is False

    @pytest.mark.asyncio
    async def test_disable_mfa(self) -> None:
        svc = AuthService()
        await svc.enable_mfa("user-1")
        assert await svc.disable_mfa("user-1") is True
        assert svc.get_mfa_state("user-1") is None

    @pytest.mark.asyncio
    async def test_disable_mfa_not_enabled(self) -> None:
        svc = AuthService()
        assert await svc.disable_mfa("user-1") is False
