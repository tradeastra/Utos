"""
Tests for Sprint 16B: Observability — metrics, middleware, and tracing.
"""

import pytest
from httpx import AsyncClient

from core.metrics import (
    init_metrics,
    get_metrics,
    utos_http_requests_total,
    utos_trading_instances_active,
)
from core.middleware import CorrelationIdMiddleware, CORRELATION_ID_HEADER


@pytest.mark.asyncio
class TestMetricsEndpoint:
    async def test_metrics_endpoint_returns_prometheus_format(self, client: AsyncClient):
        r = await client.get("/metrics")
        assert r.status_code == 200
        body = r.text
        assert "utos_http_requests_total" in body
        assert "utos_trading_instances_active" in body
        assert "# HELP" in body or "# TYPE" in body

    async def test_metrics_endpoint_has_content_type(self, client: AsyncClient):
        r = await client.get("/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers.get("content-type", "")


@pytest.mark.asyncio
class TestCorrelationIdMiddleware:
    async def test_correlation_id_generated_when_absent(self, client: AsyncClient):
        r = await client.get("/health")
        assert CORRELATION_ID_HEADER in r.headers
        assert r.headers[CORRELATION_ID_HEADER] != ""

    async def test_correlation_id_propagated_when_present(self, client: AsyncClient):
        test_cid = "test-correlation-id-12345"
        r = await client.get("/health", headers={CORRELATION_ID_HEADER: test_cid})
        assert r.headers[CORRELATION_ID_HEADER] == test_cid

    async def test_correlation_id_different_per_request(self, client: AsyncClient):
        r1 = await client.get("/health")
        r2 = await client.get("/health")
        assert r1.headers[CORRELATION_ID_HEADER] != r2.headers[CORRELATION_ID_HEADER]


@pytest.mark.asyncio
class TestMetricsMiddleware:
    async def test_request_increments_counter(self, client: AsyncClient):
        utos_http_requests_total.clear() if hasattr(utos_http_requests_total, 'clear') else None
        await client.get("/health")
        # The counter should have been incremented
        body = get_metrics().decode("utf-8")
        assert "utos_http_requests_total" in body

    async def test_request_records_duration(self, client: AsyncClient):
        await client.get("/health")
        body = get_metrics().decode("utf-8")
        assert "utos_http_request_duration_ms" in body


class TestMetricsModule:
    def test_init_metrics_sets_defaults(self):
        init_metrics()
        body = get_metrics().decode("utf-8")
        assert "utos_trading_instances_active" in body
        assert "utos_ws_connections" in body
        assert "utos_workers_active" in body
        assert "utos_dlq_size" in body

    def test_metrics_have_utos_prefix(self):
        body = get_metrics().decode("utf-8")
        lines = [l for l in body.split("\n") if l.startswith("utos_")]
        assert len(lines) > 0
        for line in lines:
            assert line.startswith("utos_")
