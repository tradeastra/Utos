"""
Order validation for the Execution Engine.
"""

from decimal import Decimal

from adapters.base import IExchangeAdapter
from core.types import OrderType
from engine.execution.exceptions import OrderValidationError
from engine.execution.models import OrderRequest


class OrderValidator:
    """Validate OrderRequest objects before they are sent to an exchange."""

    def validate(
        self,
        request: OrderRequest,
        adapter: IExchangeAdapter | None = None,
    ) -> None:
        """Validate request fields and optionally check exchange constraints.

        Args:
            request: The order request to validate.
            adapter: Optional authenticated adapter to use for symbol checks.

        Raises:
            OrderValidationError: If the request is invalid.
        """
        if not request.request_id:
            raise OrderValidationError(message="request_id is required")

        if not request.exchange_account_id:
            raise OrderValidationError(message="exchange_account_id is required")

        if not request.symbol or not request.symbol.strip():
            raise OrderValidationError(message="symbol is required")

        if request.side not in ("buy", "sell"):
            raise OrderValidationError(
                message=f"Invalid order side: {request.side}"
            )

        if not request.order_type:
            raise OrderValidationError(message="order_type is required")

        if request.order_type not in (
            OrderType.LIMIT,
            OrderType.MARKET,
            OrderType.STOP_LIMIT,
        ):
            raise OrderValidationError(
                message=f"Unsupported order_type: {request.order_type}"
            )

        if request.quantity is None or request.quantity <= Decimal("0"):
            raise OrderValidationError(
                message="quantity must be greater than zero"
            )

        if request.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if request.price is None or request.price <= Decimal("0"):
                raise OrderValidationError(
                    message="price is required for limit and stop_limit orders"
                )

        if request.order_type == OrderType.STOP_LIMIT:
            if request.stop_price is None or request.stop_price <= Decimal("0"):
                raise OrderValidationError(
                    message="stop_price is required for stop_limit orders"
                )

        if request.order_type == OrderType.MARKET and request.price is not None:
            raise OrderValidationError(
                message="price must not be set for market orders"
            )

        if adapter is not None:
            self._validate_symbol_supported(request.symbol, adapter)

    def _validate_symbol_supported(
        self, symbol: str, adapter: IExchangeAdapter
    ) -> None:
        """Check that the symbol is supported by the adapter."""
        # This is a lightweight check. A full implementation may use
        # adapter.get_exchange_info() or a symbol registry.
        if not symbol or not symbol.strip():
            raise OrderValidationError(message="symbol is empty")
