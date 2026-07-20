"""
Exchange error mapping infrastructure — Sprint 3.

Defines a generic ErrorMapper that translates raw HTTP and WebSocket
errors into domain-specific `ExchangeError` exceptions.
"""

from typing import Any

from core.exceptions import (
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
)


class ErrorMapper:
    """Map external exchange errors into domain exceptions."""

    def __init__(self, exchange_name: str) -> None:
        self.exchange_name = exchange_name

    def map_http_error(
        self,
        status_code: int,
        body: Any = None,
        message: str | None = None,
    ) -> ExchangeError:
        """Map an HTTP error response to an `ExchangeError`."""
        default_message = message or f"HTTP {status_code} from {self.exchange_name}"
        details = {"status_code": status_code, "body": body}

        if status_code == 429:
            return ExchangeRateLimitError(
                message=default_message,
                exchange_name=self.exchange_name,
                error_code="RATE_LIMIT",
                details=details,
            )

        if status_code >= 500 or status_code in {502, 503, 504}:
            return ExchangeConnectionError(
                message=default_message,
                exchange_name=self.exchange_name,
                error_code="SERVER_ERROR",
                details=details,
            )

        if status_code >= 400:
            return ExchangeError(
                message=default_message,
                exchange_name=self.exchange_name,
                error_code="HTTP_ERROR",
                details=details,
            )

        return ExchangeError(
            message=default_message,
            exchange_name=self.exchange_name,
            error_code="UNKNOWN",
            details=details,
        )

    def map_network_error(
        self, exception: Exception, message: str | None = None
    ) -> ExchangeConnectionError:
        """Map a network-level exception to an `ExchangeConnectionError`."""
        default_message = (
            message or f"Network error for {self.exchange_name}: {exception}"
        )
        return ExchangeConnectionError(
            message=default_message,
            exchange_name=self.exchange_name,
            error_code="NETWORK_ERROR",
            details={"exception": str(exception)},
        )

    def map_websocket_error(
        self, exception: Exception, message: str | None = None
    ) -> ExchangeError:
        """Map a WebSocket error to an `ExchangeError`."""
        default_message = (
            message or f"WebSocket error for {self.exchange_name}: {exception}"
        )
        return ExchangeError(
            message=default_message,
            exchange_name=self.exchange_name,
            error_code="WEBSOCKET_ERROR",
            details={"exception": str(exception)},
        )
