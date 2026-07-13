"""
OrderExecutor: dispatch orders to an exchange adapter with retry logic.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from adapters.base import IExchangeAdapter
from core.exceptions import (
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
    InsufficientBalanceError,
    TimeoutError,
    RetryableError,
)
from core.types import OrderResult
from engine.execution.exceptions import OrderExecutionError
from engine.execution.models import OrderRequest


class OrderExecutor:
    """Executes validated OrderRequest objects against an IExchangeAdapter.

    Retry policy:
      - Retry on transient errors: connection, rate limit, timeout, RetryableError.
      - Do not retry on validation, insufficient balance, or terminal exchange errors.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_multiplier: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier

    async def execute(
        self,
        request: OrderRequest,
        adapter: IExchangeAdapter,
    ) -> OrderResult:
        """Place the order on the exchange, retrying transient failures.

        Args:
            request: Validated order request.
            adapter: Authenticated exchange adapter.

        Returns:
            OrderResult from the exchange.

        Raises:
            OrderExecutionError: If placement ultimately fails.
        """
        last_error: Exception | None = None
        delay = self.base_delay

        for attempt in range(self.max_retries):
            try:
                return await adapter.place_order(
                    symbol=request.symbol.upper(),
                    side=request.side.value,
                    order_type=request.order_type.value,
                    quantity=request.quantity,
                    price=request.price,
                    stop_price=request.stop_price,
                    client_order_id=request.client_order_id,
                )
            except (
                ExchangeConnectionError,
                ExchangeRateLimitError,
                TimeoutError,
                RetryableError,
            ) as exc:
                last_error = exc
                if attempt == self.max_retries - 1:
                    break
                await asyncio.sleep(delay)
                delay = min(delay * self.backoff_multiplier, self.max_delay)
            except (ExchangeError, InsufficientBalanceError) as exc:
                # Non-transient exchange error (e.g., insufficient balance, invalid price).
                raise OrderExecutionError(
                    message=f"Order execution failed: {exc}",
                    exchange_name=adapter.exchange_name,
                    error_code=getattr(exc, "error_code", None),
                ) from exc

        raise OrderExecutionError(
            message=(
                f"Order execution failed after {self.max_retries} attempts: "
                f"{last_error}"
            ),
            exchange_name=adapter.exchange_name,
        )

    async def cancel(
        self,
        symbol: str,
        order_id: str,
        adapter: IExchangeAdapter,
    ) -> bool:
        """Cancel an order on the exchange.

        Args:
            symbol: Trading symbol.
            order_id: Exchange order ID.
            adapter: Authenticated exchange adapter.

        Returns:
            True if cancellation was accepted by the exchange.

        Raises:
            OrderExecutionError: If cancellation fails.
        """
        try:
            return await adapter.cancel_order(symbol.upper(), order_id)
        except ExchangeError as exc:
            raise OrderExecutionError(
                message=f"Cancel order failed: {exc}",
                exchange_name=adapter.exchange_name,
                error_code=getattr(exc, "error_code", None),
            ) from exc

    async def get_order(
        self,
        symbol: str,
        order_id: str,
        adapter: IExchangeAdapter,
    ) -> OrderResult:
        """Fetch current order state from the exchange.

        Args:
            symbol: Trading symbol.
            order_id: Exchange order ID.
            adapter: Authenticated exchange adapter.

        Returns:
            Latest OrderResult from the exchange.

        Raises:
            OrderExecutionError: If the exchange query fails.
        """
        try:
            return await adapter.get_order(symbol.upper(), order_id)
        except ExchangeError as exc:
            raise OrderExecutionError(
                message=f"Get order failed: {exc}",
                exchange_name=adapter.exchange_name,
                error_code=getattr(exc, "error_code", None),
            ) from exc

    async def get_open_orders(
        self,
        symbol: str | None,
        adapter: IExchangeAdapter,
    ) -> list[OrderResult]:
        """Fetch open orders from the exchange.

        Args:
            symbol: Optional symbol filter.
            adapter: Authenticated exchange adapter.

        Returns:
            List of open OrderResult objects.
        """
        try:
            return await adapter.get_open_orders(symbol.upper() if symbol else None)
        except ExchangeError as exc:
            raise OrderExecutionError(
                message=f"Get open orders failed: {exc}",
                exchange_name=adapter.exchange_name,
                error_code=getattr(exc, "error_code", None),
            ) from exc
