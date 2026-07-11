"""
Token-bucket rate limiter — Sprint 3.

Supports per-endpoint rate limits for REST and WebSocket calls.
In-memory implementation; later sprints can swap to a Redis-backed limiter.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a bucket."""

    max_tokens: float
    refill_rate: float  # tokens per second


class RateLimiter:
    """Token-bucket rate limiter with per-endpoint buckets."""

    def __init__(self, default: Optional[RateLimitConfig] = None) -> None:
        self._default = default or RateLimitConfig(max_tokens=120.0, refill_rate=120.0)
        self._configs: dict[str, RateLimitConfig] = {}
        self._tokens: dict[str, float] = defaultdict(
            lambda: self._default.max_tokens
        )
        self._last_update: dict[str, float] = defaultdict(time.monotonic)
        self._lock = asyncio.Lock()

    def configure(self, endpoint: str, config: RateLimitConfig) -> None:
        """Configure a bucket for a specific endpoint."""
        self._configs[endpoint] = config
        self._tokens[endpoint] = config.max_tokens

    def get_config(self, endpoint: str) -> RateLimitConfig:
        """Return the config for an endpoint, falling back to default."""
        return self._configs.get(endpoint, self._default)

    def _refill(self, endpoint: str) -> None:
        """Refill tokens for an endpoint based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update[endpoint]
        self._last_update[endpoint] = now

        config = self.get_config(endpoint)
        self._tokens[endpoint] = min(
            config.max_tokens,
            self._tokens[endpoint] + elapsed * config.refill_rate,
        )

    async def acquire(self, endpoint: str, tokens: float = 1.0) -> float:
        """Acquire `tokens` from the bucket for an endpoint.

        Returns the number of seconds waited. Raises `ValueError` if the
        requested tokens exceed the bucket capacity.
        """
        if tokens <= 0:
            return 0.0

        async with self._lock:
            config = self.get_config(endpoint)
            if tokens > config.max_tokens:
                raise ValueError(
                    f"Request tokens ({tokens}) exceed bucket capacity ({config.max_tokens})"
                )

            waited = 0.0
            while True:
                self._refill(endpoint)
                if self._tokens[endpoint] >= tokens:
                    self._tokens[endpoint] -= tokens
                    return waited

                deficit = tokens - self._tokens[endpoint]
                wait_time = deficit / config.refill_rate
                await asyncio.sleep(wait_time)
                waited += wait_time

    def can_acquire(self, endpoint: str, tokens: float = 1.0) -> bool:
        """Return True if the endpoint has enough tokens without blocking."""
        self._refill(endpoint)
        return self._tokens[endpoint] >= tokens

    def reset(self, endpoint: Optional[str] = None) -> None:
        """Reset token buckets for an endpoint or all endpoints."""
        if endpoint is None:
            self._tokens.clear()
            self._last_update.clear()
            return

        config = self.get_config(endpoint)
        self._tokens[endpoint] = config.max_tokens
        self._last_update[endpoint] = time.monotonic()
