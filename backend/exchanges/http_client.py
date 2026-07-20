"""
Exchange HTTP client with retry, timeout, and rate limiting — Sprint 3.

This is a generic wrapper around `httpx.AsyncClient` and does not contain
any exchange-specific logic.
"""

import asyncio
from typing import Any

import httpx
from core.exceptions import TimeoutError
from core.logging import get_logger

from exchanges.errors import ErrorMapper
from exchanges.rate_limiter import RateLimiter
from exchanges.retry import RetryPolicy

logger = get_logger(__name__)


class HttpClient:
    """Async HTTP client with configurable timeout, retry, and rate limiting."""

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        exchange_name: str = "",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_policy = retry_policy or RetryPolicy()
        self.rate_limiter = rate_limiter
        self.exchange_name = exchange_name
        self.error_mapper = ErrorMapper(exchange_name or "exchange")
        self._client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        endpoint_key: str = "default",
        rate_limit_tokens: float = 1.0,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform an HTTP request with retry and rate limiting."""
        if self.rate_limiter is not None:
            await self.rate_limiter.acquire(endpoint_key, rate_limit_tokens)

        method = method.upper()
        url = self._url(path)
        attempt = 0
        last_exception: Exception | None = None

        while True:
            attempt += 1
            try:
                client = self._get_client()
                response = await client.request(
                    method,
                    url,
                    timeout=httpx.Timeout(self.timeout, connect=10.0),
                    **kwargs,
                )

                if response.status_code < 500:
                    return response

                if not self.retry_policy.should_retry_status(response.status_code):
                    return response

                if not self.retry_policy.should_retry(attempt):
                    return response

                delay = self.retry_policy.delay_for(attempt)
                logger.warning(
                    f"{self.exchange_name} HTTP {response.status_code} "
                    f"attempt {attempt} retrying in {delay}s: {url}"
                )
                await asyncio.sleep(delay)

            except httpx.TimeoutException as exc:
                last_exception = exc
                if not self.retry_policy.should_retry(attempt, exc):
                    raise TimeoutError(
                        f"HTTP request timed out after {attempt} attempts: {url}",
                        timeout_seconds=self.timeout,
                    ) from exc

                delay = self.retry_policy.delay_for(attempt)
                logger.warning(
                    f"{self.exchange_name} HTTP timeout, retrying in {delay}s: {url}"
                )
                await asyncio.sleep(delay)

            except (httpx.NetworkError, httpx.ConnectError) as exc:
                last_exception = exc
                if not self.retry_policy.should_retry(attempt, exc):
                    raise self.error_mapper.map_network_error(exc) from exc

                delay = self.retry_policy.delay_for(attempt)
                logger.warning(
                    f"{self.exchange_name} HTTP network error, retrying in {delay}s: {url}"
                )
                await asyncio.sleep(delay)

        raise self.error_mapper.map_network_error(
            last_exception or Exception("HTTP request failed")
        )

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Convenience GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Convenience POST request."""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Convenience PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Convenience DELETE request."""
        return await self.request("DELETE", path, **kwargs)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
