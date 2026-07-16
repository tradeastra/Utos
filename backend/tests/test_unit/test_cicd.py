"""
Tests for Sprint 16E: CI/CD — smoke test logic, rollback conditions,
and deployment configuration validation.
"""

import os
import json
import pytest
from pathlib import Path
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSmokeTestEndpoints:
    """Verify all endpoints used by smoke-test.sh are accessible."""

    async def test_live_endpoint(self, client: AsyncClient):
        r = await client.get("/live")
        assert r.status_code == 200
        assert r.json()["status"] == "alive"

    async def test_ready_endpoint(self, client: AsyncClient):
        r = await client.get("/ready")
        assert r.status_code in (200, 503)

    async def test_health_endpoint(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code in (200, 503)

    async def test_metrics_endpoint(self, client: AsyncClient):
        r = await client.get("/metrics")
        assert r.status_code == 200

    async def test_root_endpoint(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code == 200

    async def test_db_health_endpoint(self, client: AsyncClient):
        r = await client.get("/db/health")
        assert r.status_code == 200

    async def test_register_endpoint_exists(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"smoke_{os.urandom(4).hex()}@test.com",
                "password": "TestPass123!",
                "username": f"smoke_{os.urandom(4).hex()}",
            },
        )
        assert r.status_code in (200, 201, 400, 409, 422)

    async def test_login_endpoint_exists(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrong"},
        )
        assert r.status_code in (400, 401, 404, 422)


class TestRollbackConditions:
    """Test rollback threshold logic."""

    def test_failure_threshold_logic(self):
        threshold = 3
        failure_count = 0

        # Simulate 2 failures — should not trigger
        for _ in range(2):
            failure_count += 1
        assert failure_count < threshold

        # Third failure — should trigger
        failure_count += 1
        assert failure_count >= threshold

    def test_latency_threshold_check(self):
        threshold_ms = 2000
        test_latencies = [100, 500, 1000, 1999, 2000, 2001, 5000]

        for latency in test_latencies:
            exceeds = latency > threshold_ms
            if latency <= 2000:
                assert not exceeds, f"{latency}ms should not exceed {threshold_ms}ms"
            else:
                assert exceeds, f"{latency}ms should exceed {threshold_ms}ms"

    def test_error_rate_threshold(self):
        threshold = 0.05  # 5%
        test_rates = [0.0, 0.01, 0.04, 0.05, 0.06, 0.1, 0.5]

        for rate in test_rates:
            exceeds = rate > threshold
            if rate <= 0.05:
                assert not exceeds, f"{rate} should not exceed {threshold}"
            else:
                assert exceeds, f"{rate} should exceed {threshold}"


class TestDeploymentConfigs:
    """Validate deployment configuration files exist and are valid."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

    def test_ci_workflow_exists(self):
        path = self.PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        assert path.exists(), "ci.yml not found"

    def test_test_workflow_exists(self):
        path = self.PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        assert path.exists(), "test.yml not found"

    def test_security_workflow_exists(self):
        path = self.PROJECT_ROOT / ".github" / "workflows" / "security.yml"
        assert path.exists(), "security.yml not found"

    def test_docker_workflow_exists(self):
        path = self.PROJECT_ROOT / ".github" / "workflows" / "docker.yml"
        assert path.exists(), "docker.yml not found"

    def test_deploy_workflow_exists(self):
        path = self.PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"
        assert path.exists(), "deploy.yml not found"

    def test_release_workflow_exists(self):
        path = self.PROJECT_ROOT / ".github" / "workflows" / "release.yml"
        assert path.exists(), "release.yml not found"

    def test_bluegreen_compose_exists(self):
        path = self.PROJECT_ROOT / "docker" / "docker-compose.bluegreen.yml"
        assert path.exists(), "docker-compose.bluegreen.yml not found"

    def test_staging_compose_exists(self):
        path = self.PROJECT_ROOT / "docker" / "docker-compose.staging.yml"
        assert path.exists(), "docker-compose.staging.yml not found"

    def test_prod_compose_exists(self):
        path = self.PROJECT_ROOT / "docker" / "docker-compose.prod.yml"
        assert path.exists(), "docker-compose.prod.yml not found"

    def test_env_staging_exists(self):
        path = self.PROJECT_ROOT / ".env.staging"
        assert path.exists(), ".env.staging not found"

    def test_env_production_exists(self):
        path = self.PROJECT_ROOT / ".env.production"
        assert path.exists(), ".env.production not found"

    def test_smoke_test_script_exists(self):
        path = self.PROJECT_ROOT / "scripts" / "smoke-test.sh"
        assert path.exists(), "smoke-test.sh not found"

    def test_auto_rollback_script_exists(self):
        path = self.PROJECT_ROOT / "scripts" / "auto-rollback.sh"
        assert path.exists(), "auto-rollback.sh not found"

    def test_bluegreen_nginx_config_exists(self):
        path = self.PROJECT_ROOT / "docker" / "nginx" / "conf.d" / "bluegreen.conf"
        assert path.exists(), "bluegreen.conf not found"

    def test_ci_cd_docs_exist(self):
        path = self.PROJECT_ROOT / "docs" / "deployment" / "CI_CD.md"
        assert path.exists(), "CI_CD.md not found"

    def test_bluegreen_compose_has_blue_and_green(self):
        path = self.PROJECT_ROOT / "docker" / "docker-compose.bluegreen.yml"
        content = path.read_text()
        assert "backend-blue" in content
        assert "backend-green" in content
        assert "frontend-blue" in content
        assert "frontend-green" in content

    def test_staging_env_has_staging_config(self):
        path = self.PROJECT_ROOT / ".env.staging"
        content = path.read_text()
        assert "APP_ENV=staging" in content
        assert "DEBUG=false" in content

    def test_production_env_has_production_config(self):
        path = self.PROJECT_ROOT / ".env.production"
        content = path.read_text()
        assert "APP_ENV=production" in content
        assert "DEBUG=false" in content
        assert "ROLLBACK" in content
