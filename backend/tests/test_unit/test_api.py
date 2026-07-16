"""
API integration tests — Sprint 01 scope.

Tests: root, health, register, login, refresh, logout, users/me.
Requires a running PostgreSQL test database (provided by conftest fixtures).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRoot:
    async def test_root_returns_api_info(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["message"] == "UTOS Trading Engine API"
        assert "version" in body
        assert "docs" in body


@pytest.mark.asyncio
class TestHealth:
    async def test_health_endpoint_present(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code in (200, 503)
        body = r.json()
        assert body["status"] in ("healthy", "degraded")
        assert "services" in body
        assert "database" in body["services"]
        assert "redis" in body["services"]

    async def test_live_endpoint(self, client: AsyncClient):
        r = await client.get("/live")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "alive"
        assert "version" in body
        assert "timestamp" in body

    async def test_ready_endpoint(self, client: AsyncClient):
        r = await client.get("/ready")
        assert r.status_code in (200, 503)
        body = r.json()
        assert body["status"] in ("ready", "not_ready")
        assert "services" in body
        assert "database" in body["services"]
        assert "redis" in body["services"]


@pytest.mark.asyncio
class TestAuthRegister:
    async def test_register_success(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": "register@example.com", "password": "Register1!", "full_name": "Reg User"},
        )
        assert r.status_code == 201
        body = r.json()
        assert "data" in body
        assert body["data"]["email"] == "register@example.com"

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "Duplicate1!", "full_name": "Dup"}
        await client.post("/api/v1/auth/register", json=payload)
        r = await client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 409

    async def test_register_weak_password_returns_422(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "weak"},
        )
        assert r.status_code == 422

    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "StrongP@ss1!"},
        )
        assert r.status_code == 422


@pytest.mark.asyncio
class TestAuthLogin:
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "Login1234!", "full_name": "Login User"},
        )
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "Login1234!"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "loginbad@example.com", "password": "Correct1!"},
        )
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "loginbad@example.com", "password": "WrongPass1!"},
        )
        assert r.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "NoOne1234!"},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
class TestAuthRefresh:
    async def test_refresh_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "Refresh1234!", "full_name": "Ref"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "refresh@example.com", "password": "Refresh1234!"},
        )
        refresh_token = login.json()["data"]["refresh_token"]

        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body["data"]

    async def test_refresh_invalid_token_returns_401(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.real.token"})
        assert r.status_code == 401


@pytest.mark.asyncio
class TestUsersMe:
    async def test_get_me_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/users/me")
        assert r.status_code == 403

    async def test_get_me_returns_profile(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "me@example.com", "password": "Profile1234!", "full_name": "Me User"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "me@example.com", "password": "Profile1234!"},
        )
        token = login.json()["data"]["access_token"]

        r = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["data"]["email"] == "me@example.com"
        assert body["data"]["is_active"] is True
