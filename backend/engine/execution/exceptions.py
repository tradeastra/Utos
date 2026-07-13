"""
Execution engine specific exceptions.

These subclass core exceptions so callers can catch either the generic
UTOSException or the execution-specific type.
"""

from core.exceptions import (
    ExchangeError,
    OrderNotFound as CoreOrderNotFound,
    ValidationError,
)


class OrderValidationError(ValidationError):
    """Raised when an OrderRequest fails validation."""
    pass


class OrderExecutionError(ExchangeError):
    """Raised when an order execution fails on the exchange."""
    pass


class OrderNotFound(CoreOrderNotFound):
    """Raised when a tracked order cannot be found."""
    pass
