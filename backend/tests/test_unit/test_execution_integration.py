"""
Integration tests for ExecutionEngine end-to-end flows.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from core.domain_types import OrderResult, OrderSide, OrderStatus, OrderType
from engine.execution import ExecutionEngine, ExecutionOrderStatus
from engine.execution.exceptions import OrderValidationError
from engine.execution.models import OrderRequest


class SimulatedAdapter:
    """Simulated exchange adapter that supports stateful order execution."""

    def __init__(self, name: str = "binance") -> None:
        self.exchange_name = name
        self._orders: dict[str, OrderResult] = {}
        self._next_id = 0
        self._reject_next = False
        self._delay_count = 0

    def _new_id(self) -> str:
        self._next_id += 1
        return f"ex_{self._next_id}"

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
    ) -> OrderResult:
        if self._reject_next:
            self._reject_next = False
            from core.exceptions import ExchangeError

            raise ExchangeError(message="rejected", exchange_name=self.exchange_name)

        order_id = self._new_id()
        result = OrderResult(
            order_id=f"local_{order_id}",
            exchange_order_id=order_id,
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status=OrderStatus.OPEN.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._orders[order_id] = result
        return result

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        result = self._orders.get(order_id)
        if result is None:
            return False
        if result.status == OrderStatus.FILLED.value:
            from core.exceptions import OrderAlreadyFilled

            raise OrderAlreadyFilled(order_id=order_id)
        cancelled = OrderResult(
            order_id=result.order_id,
            exchange_order_id=result.exchange_order_id,
            symbol=result.symbol,
            side=result.side,
            order_type=result.order_type,
            quantity=result.quantity,
            price=result.price,
            filled_quantity=result.filled_quantity,
            average_fill_price=result.average_fill_price,
            status=OrderStatus.CANCELLED.value,
            created_at=result.created_at,
            updated_at=datetime.now(UTC),
        )
        self._orders[order_id] = cancelled
        return True

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        result = self._orders.get(order_id)
        if result is None:
            from core.exceptions import OrderNotFound as CoreOrderNotFound

            raise CoreOrderNotFound(order_id=order_id)
        return result

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        return [
            o
            for o in self._orders.values()
            if o.status == OrderStatus.OPEN.value
            and (symbol is None or o.symbol == symbol.upper())
        ]

    def reject_next(self) -> None:
        self._reject_next = True

    def fill(self, order_id: str) -> None:
        result = self._orders.get(order_id)
        if result is None:
            return
        filled = OrderResult(
            order_id=result.order_id,
            exchange_order_id=result.exchange_order_id,
            symbol=result.symbol,
            side=result.side,
            order_type=result.order_type,
            quantity=result.quantity,
            price=result.price,
            filled_quantity=result.quantity,
            average_fill_price=result.price,
            status=OrderStatus.FILLED.value,
            created_at=result.created_at,
            updated_at=datetime.now(UTC),
        )
        self._orders[order_id] = filled

    def partial_fill(
        self, order_id: str, fill_qty: Decimal, fill_price: Decimal
    ) -> None:
        result = self._orders.get(order_id)
        if result is None:
            return
        prev_filled = result.filled_quantity
        new_filled = prev_filled + fill_qty
        if result.average_fill_price is not None and prev_filled > 0:
            total_cost = result.average_fill_price * prev_filled + fill_price * fill_qty
            avg_price = total_cost / new_filled
        else:
            avg_price = fill_price
        if new_filled >= result.quantity:
            status = OrderStatus.FILLED.value
        else:
            status = OrderStatus.PARTIALLY_FILLED.value
        updated = OrderResult(
            order_id=result.order_id,
            exchange_order_id=result.exchange_order_id,
            symbol=result.symbol,
            side=result.side,
            order_type=result.order_type,
            quantity=result.quantity,
            price=result.price,
            filled_quantity=new_filled,
            average_fill_price=avg_price,
            status=status,
            created_at=result.created_at,
            updated_at=datetime.now(UTC),
        )
        self._orders[order_id] = updated


@pytest.fixture
def account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def engine(account_id: uuid.UUID) -> ExecutionEngine:
    e = ExecutionEngine()
    e.register_adapter(account_id, SimulatedAdapter())
    return e


@pytest.fixture
def make_request(account_id: uuid.UUID):
    def _make(request_id: uuid.UUID | None = None) -> OrderRequest:
        return OrderRequest(
            request_id=request_id or uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

    return _make


class TestExecutionIntegration:
    @pytest.mark.asyncio
    async def test_place_cancel_full_lifecycle(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request = make_request()
        placed = await engine.place_order(request)
        assert placed.status == OrderStatus.OPEN.value

        cancelled = await engine.cancel_order(account_id, placed.order_id)
        assert cancelled is not None
        tracked = engine.tracker.get(account_id, placed.order_id)
        assert tracked is not None
        assert tracked.status == ExecutionOrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_place_sync_fill(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request = make_request()
        placed = await engine.place_order(request)
        adapter = engine._adapters[account_id]
        adapter.fill(placed.exchange_order_id)

        synced = await engine.sync_order(account_id, placed.order_id)
        assert synced.status == OrderStatus.FILLED.value
        tracked = engine.tracker.get(account_id, placed.order_id)
        assert tracked.status == ExecutionOrderStatus.FILLED
        assert engine.list_active_orders(account_id) == []

    @pytest.mark.asyncio
    async def test_cancel_all_orders(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request1 = make_request()
        request2 = make_request()
        await engine.place_order(request1)
        await engine.place_order(request2)

        results = await engine.cancel_all_orders(account_id, "BTCUSDT")
        assert len(results) == 2
        active = engine.list_active_orders(account_id)
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_rejected_order_does_not_retry(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        adapter = engine._adapters[account_id]
        adapter.reject_next()
        request = make_request()
        from engine.execution.exceptions import OrderExecutionError

        with pytest.raises(OrderExecutionError):
            await engine.place_order(request)
        assert len(adapter._orders) == 0

    @pytest.mark.asyncio
    async def test_idempotency_after_failure(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        """Duplicate request_id after failure should return the failed cached result."""
        request_id = uuid.uuid4()
        request = make_request(request_id)
        adapter = engine._adapters[account_id]
        adapter.reject_next()

        from engine.execution.exceptions import OrderExecutionError

        with pytest.raises(OrderExecutionError):
            await engine.place_order(request)

        # Second call with same request_id must return cached failed result, not hit exchange.
        cached = await engine.place_order(request)
        assert cached.error_message is not None
        assert cached.status == OrderStatus.REJECTED.value
        assert len(adapter._orders) == 0

    @pytest.mark.asyncio
    async def test_cancel_filled_order_fails(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request = make_request()
        placed = await engine.place_order(request)
        adapter = engine._adapters[account_id]
        adapter.fill(placed.exchange_order_id)
        await engine.sync_order(account_id, placed.order_id)

        # Simulated adapter will raise OrderAlreadyFilled.
        result = await engine.cancel_order(account_id, placed.order_id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_orders_isolated_by_account(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        other_account = uuid.uuid4()
        engine.register_adapter(other_account, SimulatedAdapter("bybit"))

        await engine.place_order(make_request())
        await engine.place_order(make_request())
        other_request = make_request()
        other_request.exchange_account_id = other_account
        await engine.place_order(other_request)

        assert len(engine.list_active_orders(account_id)) == 2
        assert len(engine.list_active_orders(other_account)) == 1
        assert len(engine.list_active_orders()) == 3

    @pytest.mark.asyncio
    async def test_validation_rejects_invalid_order(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request = make_request()
        request.quantity = Decimal("-1")
        with pytest.raises(OrderValidationError):
            await engine.place_order(request)


class RaceConditionAdapter(SimulatedAdapter):
    """Adapter that introduces network latency in cancel_order to simulate race conditions."""

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        await asyncio.sleep(0.05)
        return await super().cancel_order(symbol, order_id)


class TestIdempotencyScenario:
    """Test: place_order(request_id='abc') → timeout → retry → only 1 order on exchange."""

    @pytest.mark.asyncio
    async def test_timeout_retry_produces_single_order(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request_id = uuid.uuid4()
        request = make_request(request_id)

        # First call succeeds — order placed on exchange.
        result1 = await engine.place_order(request)
        assert result1.status == OrderStatus.OPEN.value

        # Caller experiences timeout and retries with same request_id.
        result2 = await engine.place_order(request)

        # Same order returned, no second exchange call.
        assert result1.order_id == result2.order_id
        assert result1.exchange_order_id == result2.exchange_order_id
        adapter = engine._adapters[account_id]
        assert len(adapter._orders) == 1

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_request_single_order(
        self, account_id: uuid.UUID
    ) -> None:
        """Two concurrent place_order calls with same request_id → only 1 order."""
        e = ExecutionEngine()
        e.register_adapter(account_id, SimulatedAdapter())
        request_id = uuid.uuid4()
        request = OrderRequest(
            request_id=request_id,
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

        result1, result2 = await asyncio.gather(
            e.place_order(request),
            e.place_order(request),
        )

        assert result1.order_id == result2.order_id
        adapter = e._adapters[account_id]
        assert len(adapter._orders) == 1


class TestPartialFillScenario:
    """Test: OPEN → PARTIALLY_FILLED → PARTIALLY_FILLED → FILLED with consistent quantities."""

    @pytest.mark.asyncio
    async def test_partial_fill_lifecycle(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        request = make_request()
        request.quantity = Decimal("0.1")
        placed = await engine.place_order(request)
        adapter = engine._adapters[account_id]

        # OPEN → PARTIALLY_FILLED (0.03 @ 49900)
        adapter.partial_fill(
            placed.exchange_order_id, Decimal("0.03"), Decimal("49900")
        )
        synced1 = await engine.sync_order(account_id, placed.order_id)
        assert synced1.status == OrderStatus.PARTIALLY_FILLED.value
        assert synced1.filled_quantity == Decimal("0.03")
        assert synced1.average_fill_price == Decimal("49900")
        tracked = engine.tracker.get(account_id, placed.order_id)
        assert tracked.status == ExecutionOrderStatus.PARTIALLY_FILLED

        # PARTIALLY_FILLED → PARTIALLY_FILLED (0.04 @ 50100)
        adapter.partial_fill(
            placed.exchange_order_id, Decimal("0.04"), Decimal("50100")
        )
        synced2 = await engine.sync_order(account_id, placed.order_id)
        assert synced2.status == OrderStatus.PARTIALLY_FILLED.value
        assert synced2.filled_quantity == Decimal("0.07")
        tracked = engine.tracker.get(account_id, placed.order_id)
        assert tracked.status == ExecutionOrderStatus.PARTIALLY_FILLED

        # PARTIALLY_FILLED → FILLED (0.03 @ 50050)
        adapter.partial_fill(
            placed.exchange_order_id, Decimal("0.03"), Decimal("50050")
        )
        synced3 = await engine.sync_order(account_id, placed.order_id)
        assert synced3.status == OrderStatus.FILLED.value
        assert synced3.filled_quantity == Decimal("0.1")
        tracked = engine.tracker.get(account_id, placed.order_id)
        assert tracked.status == ExecutionOrderStatus.FILLED

        # Average price consistency: (0.03*49900 + 0.04*50100 + 0.03*50050) / 0.1
        expected_avg = (
            Decimal("0.03") * Decimal("49900")
            + Decimal("0.04") * Decimal("50100")
            + Decimal("0.03") * Decimal("50050")
        ) / Decimal("0.1")
        assert synced3.average_fill_price == expected_avg

        # Order no longer active
        assert engine.list_active_orders(account_id) == []


class TestCancelRaceScenario:
    """Test: Order FILLED + Cancel sent concurrently → Engine does not corrupt."""

    @pytest.mark.asyncio
    async def test_cancel_after_fill_returns_filled(
        self, engine: ExecutionEngine, make_request, account_id: uuid.UUID
    ) -> None:
        """Cancel arrives after order already filled — engine syncs and returns FILLED."""
        request = make_request()
        placed = await engine.place_order(request)
        adapter = engine._adapters[account_id]

        # Order fills on exchange before cancel reaches it.
        adapter.fill(placed.exchange_order_id)

        result = await engine.cancel_order(account_id, placed.order_id)
        assert result.status == OrderStatus.FILLED.value

        tracked = engine.tracker.get(account_id, placed.order_id)
        assert tracked is not None
        assert tracked.status == ExecutionOrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_cancel_race_concurrent(self, account_id: uuid.UUID) -> None:
        """Order fills while cancel is in-flight — engine handles race gracefully."""
        adapter = RaceConditionAdapter()
        e = ExecutionEngine()
        e.register_adapter(account_id, adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        placed = await e.place_order(request)

        async def delayed_fill() -> None:
            await asyncio.sleep(0.01)
            adapter.fill(placed.exchange_order_id)

        cancel_result, _ = await asyncio.gather(
            e.cancel_order(account_id, placed.order_id),
            delayed_fill(),
        )

        # Engine should have synced and discovered FILLED, not stuck in CANCELLING.
        assert cancel_result.status == OrderStatus.FILLED.value
        tracked = e.tracker.get(account_id, placed.order_id)
        assert tracked is not None
        assert tracked.status == ExecutionOrderStatus.FILLED
        assert tracked.status != ExecutionOrderStatus.CANCELLING

    @pytest.mark.asyncio
    async def test_cancel_race_partial_fill(self, account_id: uuid.UUID) -> None:
        """Order partially fills while cancel is in-flight — engine handles gracefully."""
        adapter = RaceConditionAdapter()
        e = ExecutionEngine()
        e.register_adapter(account_id, adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        placed = await e.place_order(request)

        async def delayed_partial_fill() -> None:
            await asyncio.sleep(0.01)
            adapter.partial_fill(
                placed.exchange_order_id, Decimal("0.03"), Decimal("49900")
            )

        cancel_result, _ = await asyncio.gather(
            e.cancel_order(account_id, placed.order_id),
            delayed_partial_fill(),
        )

        # Engine must not be stuck in CANCELLING — it should reach a terminal state.
        tracked = e.tracker.get(account_id, placed.order_id)
        assert tracked is not None
        assert tracked.status != ExecutionOrderStatus.CANCELLING
        assert tracked.status in {
            ExecutionOrderStatus.CANCELLED,
            ExecutionOrderStatus.PARTIALLY_FILLED,
            ExecutionOrderStatus.FILLED,
        }
        # Engine did not crash and tracker is consistent.
        assert cancel_result is not None
