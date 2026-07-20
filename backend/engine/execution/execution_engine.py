"""
ExecutionEngine — the single entry point for placing and managing orders.

The engine is intentionally narrow: it accepts OrderRequest objects, validates
them, delegates to an IExchangeAdapter, tracks state, and handles retry and
idempotency. It does not implement grid, DCA, strategy, or profit-lock logic.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from adapters.base import IExchangeAdapter
from core.domain_types import OrderResult, OrderStatus
from core.exceptions import OrderAlreadyFilled
from core.logging import get_logger

from engine.execution.exceptions import OrderExecutionError, OrderNotFound
from engine.execution.executor import OrderExecutor
from engine.execution.models import ExecutionOrderStatus, OrderRequest, TrackedOrder
from engine.execution.order_state import OrderStateMachine
from engine.execution.tracker import OrderTracker
from engine.execution.validator import OrderValidator

logger = get_logger(__name__)


class ExecutionEngine:
    """Facade for placing, cancelling, syncing, and tracking orders."""

    def __init__(
        self,
        validator: OrderValidator | None = None,
        executor: OrderExecutor | None = None,
        tracker: OrderTracker | None = None,
    ) -> None:
        self.validator = validator or OrderValidator()
        self.executor = executor or OrderExecutor()
        self.tracker = tracker or OrderTracker()
        self._adapters: dict[uuid.UUID, IExchangeAdapter] = {}

    def register_adapter(
        self, exchange_account_id: uuid.UUID, adapter: IExchangeAdapter
    ) -> None:
        """Register an authenticated exchange adapter for an account."""
        self._adapters[exchange_account_id] = adapter
        logger.info(
            "Registered execution adapter",
            extra={
                "exchange_account_id": str(exchange_account_id),
                "exchange": adapter.exchange_name,
            },
        )

    def unregister_adapter(self, exchange_account_id: uuid.UUID) -> None:
        """Remove an adapter registration."""
        self._adapters.pop(exchange_account_id, None)

    def _get_adapter(self, exchange_account_id: uuid.UUID) -> IExchangeAdapter:
        adapter = self._adapters.get(exchange_account_id)
        if adapter is None:
            raise OrderExecutionError(
                message=(f"No adapter registered for account {exchange_account_id}"),
                exchange_name="unknown",
            )
        return adapter

    async def place_order(self, request: OrderRequest) -> OrderResult:
        """Place an order idempotently.

        Duplicate ``request_id`` values return the cached result without hitting
        the exchange again.
        """
        cached = self.tracker.get_by_request_id(request.request_id)
        if cached is not None:
            logger.info(
                "Returning cached order result for idempotent request",
                extra={
                    "request_id": str(request.request_id),
                    "order_id": cached.result.order_id,
                },
            )
            return cached.result

        adapter = self._get_adapter(request.exchange_account_id)
        self.validator.validate(request, adapter)

        tracked = self._create_pending(request)

        try:
            self._transition(tracked, ExecutionOrderStatus.SUBMITTING)
            result = await self.executor.execute(request, adapter)
            status = OrderTracker.map_exchange_status(result.status)

            # Re-key tracker if exchange returned a different order_id
            old_order_id = tracked.result.order_id
            if result.order_id != old_order_id:
                self.tracker.re_key(
                    request.exchange_account_id,
                    old_order_id,
                    result.order_id,
                )

            self._transition(tracked, status)
            self.tracker.update(
                request.exchange_account_id,
                result.order_id,
                result,
                status=status,
            )
            return result
        except Exception as exc:  # noqa: BLE001
            final_status = ExecutionOrderStatus.FAILED
            self._transition(tracked, final_status)
            error_result = self._result_from_error(request, tracked, exc)
            self.tracker.update(
                request.exchange_account_id,
                tracked.result.order_id,
                error_result,
                status=final_status,
            )
            raise

    async def cancel_order(
        self, exchange_account_id: uuid.UUID, order_id: str
    ) -> OrderResult:
        """Cancel a single tracked order."""
        tracked = self.tracker.get(exchange_account_id, order_id)
        if tracked is None:
            raise OrderNotFound(order_id=str(order_id))

        if tracked.status in {
            ExecutionOrderStatus.FILLED,
            ExecutionOrderStatus.CANCELLED,
            ExecutionOrderStatus.REJECTED,
        }:
            return tracked.result

        adapter = self._get_adapter(exchange_account_id)
        self._transition(tracked, ExecutionOrderStatus.CANCELLING)
        try:
            await self.executor.cancel(
                tracked.result.symbol, tracked.result.exchange_order_id, adapter
            )
            self._transition(tracked, ExecutionOrderStatus.CANCELLED)
            cancelled_result = OrderResult(
                order_id=tracked.result.order_id,
                exchange_order_id=tracked.result.exchange_order_id,
                symbol=tracked.result.symbol,
                side=tracked.result.side,
                order_type=tracked.result.order_type,
                quantity=tracked.result.quantity,
                price=tracked.result.price,
                filled_quantity=tracked.result.filled_quantity,
                average_fill_price=tracked.result.average_fill_price,
                status=OrderStatus.CANCELLED.value,
                created_at=tracked.result.created_at,
                updated_at=datetime.now(UTC),
            )
            self.tracker.update(
                exchange_account_id,
                order_id,
                cancelled_result,
                status=ExecutionOrderStatus.CANCELLED,
            )
            return cancelled_result
        except (OrderExecutionError, OrderAlreadyFilled):
            result = await self.executor.get_order(
                tracked.result.symbol, tracked.result.exchange_order_id, adapter
            )
            status = OrderTracker.map_exchange_status(result.status)
            self._transition(tracked, status)
            self.tracker.update(exchange_account_id, order_id, result, status=status)
            return result

    async def cancel_all_orders(
        self,
        exchange_account_id: uuid.UUID,
        symbol: str | None = None,
    ) -> list[OrderResult]:
        """Cancel all open orders for an account, optionally filtered by symbol."""
        adapter = self._get_adapter(exchange_account_id)
        open_results = await self.executor.get_open_orders(symbol, adapter)
        results: list[OrderResult] = []
        for result in open_results:
            try:
                await self.executor.cancel(
                    result.symbol, result.exchange_order_id, adapter
                )
            except OrderExecutionError:
                # Some orders may fill between get_open_orders and cancel.
                pass
            else:
                tracked = self.tracker.get(exchange_account_id, result.order_id)
                if tracked is not None:
                    self._transition(tracked, ExecutionOrderStatus.CANCELLED)
                results.append(result)
        return results

    async def get_order(
        self, exchange_account_id: uuid.UUID, order_id: str
    ) -> OrderResult | None:
        """Return the tracked order result, or None if not tracked."""
        tracked = self.tracker.get(exchange_account_id, order_id)
        return tracked.result if tracked else None

    async def sync_order(
        self, exchange_account_id: uuid.UUID, order_id: str
    ) -> OrderResult:
        """Synchronize a tracked order with the exchange and return fresh state."""
        tracked = self.tracker.get(exchange_account_id, order_id)
        if tracked is None:
            raise OrderNotFound(order_id=str(order_id))

        adapter = self._get_adapter(exchange_account_id)
        result = await self.executor.get_order(
            tracked.result.symbol, tracked.result.exchange_order_id, adapter
        )
        status = OrderTracker.map_exchange_status(result.status)
        self._transition(tracked, status)
        self.tracker.update(exchange_account_id, order_id, result, status=status)
        return result

    def list_active_orders(
        self, exchange_account_id: uuid.UUID | None = None
    ) -> list[OrderResult]:
        """Return active order results, optionally filtered by account."""
        return [order.result for order in self.tracker.list_active(exchange_account_id)]

    def _create_pending(self, request: OrderRequest) -> TrackedOrder:
        """Create a pending tracked order before submission."""
        placeholder = OrderResult(
            order_id=self._local_order_id(),
            exchange_order_id="",
            symbol=request.symbol.upper(),
            side=request.side.value,
            order_type=request.order_type.value,
            quantity=request.quantity,
            price=request.price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status=OrderStatus.PENDING.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return self.tracker.track(
            request_id=request.request_id,
            exchange_account_id=request.exchange_account_id,
            result=placeholder,
            status=ExecutionOrderStatus.PENDING,
        )

    def _transition(self, tracked: TrackedOrder, target: ExecutionOrderStatus) -> None:
        OrderStateMachine.validate_transition(tracked.status, target)
        tracked.status = target
        tracked.touch()

    def _local_order_id(self) -> str:
        return f"local_{uuid.uuid4().hex[:12]}"

    def _result_from_error(
        self,
        request: OrderRequest,
        tracked: TrackedOrder,
        exc: Exception,
    ) -> OrderResult:
        error_message = str(exc)
        return OrderResult(
            order_id=tracked.result.order_id,
            exchange_order_id=tracked.result.exchange_order_id,
            symbol=request.symbol.upper(),
            side=request.side.value,
            order_type=request.order_type.value,
            quantity=request.quantity,
            price=request.price,
            filled_quantity=tracked.result.filled_quantity,
            average_fill_price=tracked.result.average_fill_price,
            status=OrderStatus.REJECTED.value,
            created_at=tracked.result.created_at,
            updated_at=datetime.now(UTC),
            error_message=error_message,
        )
