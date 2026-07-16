"""
Tests for Sprint 16C: Security — security headers, rate limiting,
and production secret validation.
"""

import pytest
from httpx import AsyncClient

from core.middleware import SECURITY_HEADERS, RATE_LIMITS, DEFAULT_API_LIMIT


@pytest.mark.asyncio
class TestSecurityHeaders:
    async def test_security_headers_present_on_api(self, client: AsyncClient):
        r = await client.get("/health")
        for header, expected_value in SECURITY_HEADERS.items():
            assert header in r.headers, f"Missing security header: {header}"
            assert r.headers[header] == expected_value, f"Wrong value for {header}"

    async def test_x_content_type_options(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    async def test_x_frame_options(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("X-Frame-Options") == "DENY"

    async def test_referrer_policy(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    async def test_permissions_policy(self, client: AsyncClient):
        r = await client.get("/health")
        assert "Permissions-Policy" in r.headers

    async def test_cross_origin_opener_policy(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"

    async def test_cross_origin_resource_policy(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("Cross-Origin-Resource-Policy") == "same-origin"


@pytest.mark.asyncio
class TestRateLimiting:
    async def test_auth_endpoints_have_strict_limits(self):
        assert RATE_LIMITS["/api/v1/auth/login"] == 5
        assert RATE_LIMITS["/api/v1/auth/register"] == 5

    async def test_refresh_has_moderate_limit(self):
        assert RATE_LIMITS["/api/v1/auth/refresh"] == 10

    async def test_default_api_limit(self):
        assert DEFAULT_API_LIMIT == 100

    async def test_non_api_paths_not_limited(self, client: AsyncClient):
        # /health and /metrics should not be rate limited
        for _ in range(10):
            r = await client.get("/health")
            assert r.status_code in (200, 503)


class TestProductionSecretValidation:
    def test_development_allows_default_secret(self):
        from core.config import Settings
        # In development, default SECRET_KEY is allowed
        s = Settings(APP_ENV="development", TESTING=True)
        assert s.SECRET_KEY == "change-me-to-a-long-random-string-at-least-32-chars"

    def test_production_rejects_default_secret(self):
        from pydantic import ValidationError
        from core.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(APP_ENV="production", SECRET_KEY="change-me-to-a-long-random-string-at-least-32-chars")

    def test_production_rejects_short_secret(self):
        from pydantic import ValidationError
        from core.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(APP_ENV="production", SECRET_KEY="short")

    def test_production_rejects_debug_true(self):
        from pydantic import ValidationError
        from core.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(APP_ENV="production", SECRET_KEY="a" * 32, DEBUG=True)

    def test_production_accepts_valid_config(self):
        from core.config import Settings
        s = Settings(APP_ENV="production", SECRET_KEY="a" * 32, DEBUG=False)
        assert s.APP_ENV == "production"
        assert s.DEBUG is False
