"""
Middleware for UTOS Trading Engine.

- CorrelationIdMiddleware: injects/propagates correlation IDs
- MetricsMiddleware: records Prometheus metrics for all HTTP requests
"""

import time
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging import set_correlation_id, get_correlation_id
from core.metrics import (
    utos_http_requests_total,
    utos_http_request_duration_ms,
)

# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject or propagate correlation IDs for request tracing."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Check incoming header or generate new
        cid = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        set_correlation_id(cid)

        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = cid
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record Prometheus metrics for every HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        method = request.method
        # Normalize path to avoid high cardinality
        path = request.url.path
        # Group dynamic paths (e.g., /api/v1/trading-instances/123 -> /api/v1/trading-instances/{id})
        if "/trading-instances/" in path:
            path = "/api/v1/trading-instances/{id}"
        elif "/users/" in path:
            path = "/api/v1/users/{id}"

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            utos_http_requests_total.labels(
                method=method,
                endpoint=path,
                status=status,
            ).inc()
            utos_http_request_duration_ms.labels(
                method=method,
                endpoint=path,
            ).observe(duration_ms)

        return response
