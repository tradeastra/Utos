"""
Core exceptions for UTOS Trading Engine.

This module defines the fundamental exception types used throughout the system.
"""


class UTOSException(Exception):
    """Base exception for all UTOS Trading Engine errors."""

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ValidationError(UTOSException):
    """Raised when input validation fails."""

    pass


class AuthenticationError(UTOSException):
    """Raised when authentication fails."""

    pass


class AuthorizationError(UTOSException):
    """Raised when authorization fails."""

    pass


class ExchangeError(UTOSException):
    """Raised when exchange operations fail."""

    def __init__(
        self,
        message: str,
        exchange_name: str,
        error_code: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, error_code, details)
        self.exchange_name = exchange_name


class ExchangeConnectionError(ExchangeError):
    """Raised when exchange connection fails."""

    pass


class ExchangeRateLimitError(ExchangeError):
    """Raised when exchange rate limit is exceeded."""

    pass


class InsufficientBalanceError(UTOSException):
    """Raised when insufficient balance for operation."""

    def __init__(
        self,
        message: str,
        required: float | None = None,
        available: float | None = None,
    ):
        super().__init__(message)
        self.required = required
        self.available = available


class InvalidStateTransition(UTOSException):
    """Raised when invalid state transition is attempted."""

    def __init__(self, message: str, current_state: str, target_state: str):
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


class RiskLimitExceeded(UTOSException):
    """Raised when risk limits are exceeded."""

    def __init__(
        self,
        message: str,
        limit_type: str,
        current_value: float | None = None,
        limit_value: float | None = None,
    ):
        super().__init__(message)
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value


class GridError(UTOSException):
    """Raised when grid operations fail."""

    pass


class ProfitLockError(UTOSException):
    """Raised when profit lock operations fail."""

    pass


class StrategyError(UTOSException):
    """Raised when strategy operations fail."""

    pass


class PortfolioError(UTOSException):
    """Raised when portfolio operations fail."""

    pass


class RiskError(UTOSException):
    """Raised when risk engine operations fail."""

    pass


class RecoveryError(UTOSException):
    """Raised when recovery operations fail."""

    pass


class ReconciliationError(UTOSException):
    """Raised when state reconciliation cannot be auto-resolved."""

    pass


class CheckpointError(UTOSException):
    """Raised when checkpoint save/load fails."""

    pass


class WorkerError(UTOSException):
    """Raised when worker operations fail."""

    pass


class EventError(UTOSException):
    """Raised when event operations fail."""

    pass


class StorageError(UTOSException):
    """Raised when storage operations fail."""

    pass


class ConfigurationError(UTOSException):
    """Raised when configuration is invalid."""

    pass


class DatabaseError(UTOSException):
    """Raised when database operations fail."""

    pass


class CacheError(UTOSException):
    """Raised when cache operations fail."""

    pass


class NotificationError(UTOSException):
    """Raised when notification operations fail."""

    pass


class TimeoutError(UTOSException):
    """Raised when operations timeout."""

    def __init__(self, message: str, timeout_seconds: float | None = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class RetryableError(UTOSException):
    """Base class for errors that can be retried."""

    def __init__(self, message: str, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(message)
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class NonRetryableError(UTOSException):
    """Base class for errors that should not be retried."""

    pass


class TradingInstanceNotFound(UTOSException):
    """Raised when trading instance is not found."""

    def __init__(self, instance_id: str):
        super().__init__(f"Trading instance {instance_id} not found")
        self.instance_id = instance_id


class OrderNotFound(UTOSException):
    """Raised when order is not found."""

    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} not found")
        self.order_id = order_id


class PositionNotFound(UTOSException):
    """Raised when position is not found."""

    def __init__(self, position_id: str):
        super().__init__(f"Position {position_id} not found")
        self.position_id = position_id


class UserNotFound(UTOSException):
    """Raised when user is not found."""

    def __init__(self, user_id: str):
        super().__init__(f"User {user_id} not found")
        self.user_id = user_id


class ExchangeAccountNotFound(UTOSException):
    """Raised when exchange account is not found."""

    def __init__(self, account_id: str):
        super().__init__(f"Exchange account {account_id} not found")
        self.account_id = account_id


class SymbolNotSupported(UTOSException):
    """Raised when symbol is not supported by exchange."""

    def __init__(self, symbol: str, exchange: str):
        super().__init__(f"Symbol {symbol} not supported by exchange {exchange}")
        self.symbol = symbol
        self.exchange = exchange


class InvalidQuantity(UTOSException):
    """Raised when quantity is invalid."""

    def __init__(
        self,
        message: str,
        quantity: float | None = None,
        min_quantity: float | None = None,
        max_quantity: float | None = None,
    ):
        super().__init__(message)
        self.quantity = quantity
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity


class InvalidPrice(UTOSException):
    """Raised when price is invalid."""

    def __init__(
        self,
        message: str,
        price: float | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ):
        super().__init__(message)
        self.price = price
        self.min_price = min_price
        self.max_price = max_price


class OrderAlreadyExists(UTOSException):
    """Raised when order already exists."""

    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} already exists")
        self.order_id = order_id


class OrderAlreadyCancelled(UTOSException):
    """Raised when trying to cancel an already cancelled order."""

    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} is already cancelled")
        self.order_id = order_id


class OrderAlreadyFilled(UTOSException):
    """Raised when trying to modify an already filled order."""

    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} is already filled")
        self.order_id = order_id


class InsufficientPermissions(UTOSException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str, required_permission: str | None = None):
        super().__init__(message)
        self.required_permission = required_permission


class SubscriptionRequired(UTOSException):
    """Raised when feature requires premium subscription."""

    def __init__(self, feature: str, required_tier: str):
        super().__init__(f"Feature {feature} requires {required_tier} subscription")
        self.feature = feature
        self.required_tier = required_tier


class MaintenanceMode(UTOSException):
    """Raised when system is in maintenance mode."""

    pass


class ServiceUnavailable(UTOSException):
    """Raised when required service is unavailable."""

    def __init__(self, service_name: str):
        super().__init__(f"Service {service_name} is unavailable")
        self.service_name = service_name
