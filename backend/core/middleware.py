"""
Middleware for UTOS Trading Engine.

- CorrelationIdMiddleware: injects/propagates correlation IDs
- MetricsMiddleware: records Prometheus metrics for all HTTP requests
- SecurityHeadersMiddleware: adds security headers to all responses
- RateLimitMiddleware: per-endpoint rate limiting via Redis sliding window
"""

import time
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from core.logging import set_correlation_id, get_correlation_id, get_logger
from core.metrics import (
    utos_http_requests_total,
    utos_http_request_duration_ms,
)

logger = get_logger(__name__)

# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"

# ── Security Headers ──────────────────────────
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# ── Rate Limiting (requests per minute) ───────
RATE_LIMITS: dict[str, int] = {
    "/api/v1/auth/login": 5,
    "/api/v1/auth/register": 5,
    "/api/v1/auth/refresh": 10,
}
DEFAULT_API_LIMIT = 100


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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all backend responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based sliding window rate limiter.

    Falls back to allowing all requests if Redis is unavailable.
    Returns 429 with Retry-After header when limit exceeded.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        limit = RATE_LIMITS.get(path, DEFAULT_API_LIMIT)
        client_ip = request.client.host if request.client else "unknown"

        redis = self._get_redis()
        if redis is None:
            return await call_next(request)

        key = f"ratelimit:{client_ip}:{path}"
        window_seconds = 60

        try:
            now = time.time()
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            count = results[2]

            if count > limit:
                logger.warning(
                    f"Rate limit exceeded for {client_ip} on {path}",
                    extra={"client_ip": client_ip, "path": path, "count": count, "limit": limit},
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded. Maximum {limit} requests per minute.",
                        }
                    },
                    headers={"Retry-After": str(window_seconds)},
                )

        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Rate limit check failed: {exc}")

        return await call_next(request)

    def _get_redis(self):
        try:
            from database.redis_client import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None
