"""
Retry policy for exchange HTTP and WebSocket operations — Sprint 3.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Type


@dataclass
class RetryPolicy:
    """Configurable retry policy for network operations."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None
    retryable_status_codes: Optional[set[int]] = None

    def __post_init__(self) -> None:
        if self.retryable_exceptions is None:
            self.retryable_exceptions = (Exception,)
        if self.retryable_status_codes is None:
            self.retryable_status_codes = {429, 500, 502, 503, 504}

    def should_retry(self, attempt: int, exception: Optional[Exception] = None) -> bool:
        """Return True if the operation should be retried."""
        if attempt >= self.max_retries:
            return False
        if exception is None:
            return True
        return isinstance(exception, self.retryable_exceptions)

    def should_retry_status(self, status_code: int) -> bool:
        """Return True if the HTTP status code is retryable."""
        return status_code in self.retryable_status_codes

    def delay_for(self, attempt: int) -> float:
        """Return the delay in seconds before the next attempt (1-indexed)."""
        import math

        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay)

    def with_overrides(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
    ) -> "RetryPolicy":
        """Return a new RetryPolicy with overridden fields."""
        return RetryPolicy(
            max_retries=max_retries or self.max_retries,
            base_delay=base_delay or self.base_delay,
            max_delay=max_delay or self.max_delay,
            exponential_base=self.exponential_base,
            retryable_exceptions=self.retryable_exceptions,
            retryable_status_codes=self.retryable_status_codes,
        )
