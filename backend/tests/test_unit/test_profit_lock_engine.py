"""
Unit tests for ProfitLockEngine.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from core.exceptions import ProfitLockError, ValidationError
from core.types import OrderResult, OrderSide, OrderStatus, OrderType
from engine.execution import ExecutionEngine
from engine.execution.models import OrderRequest
from engine.profit_lock.engine import ProfitLockEngine
from engine.profit_lock.state import ProfitLockStatus


class FakeAdapter:
    """Fake adapter for profit lock engine tests."""

    def __init__(self, name: str = "binance") -> None:
        self.exchange_name = name
        self.place_calls: list[dict[str, Any]] = []
        self.cancel_calls: list[dict[str, Any]] = []
        self._orders: dict[str, OrderResult] = {}
        self._counter = 0

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
        self.place_calls.append({
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
        })
        self._counter += 1
        order_id = f"ex_{self._counter}"
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
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._orders[order_id] = result
        return result

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        self.cancel_calls.append({"symbol": symbol, "order_id": order_id})
        return True

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        result = self._orders.get(order_id)
        if result is None:
            from core.exceptions import OrderNotFound
            raise OrderNotFound(order_id=order_id)
        return result

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        return []


@pytest.fixture
def account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def execution_engine(account_id: uuid.UUID, fake_adapter: FakeAdapter) -> ExecutionEngine:
    e = ExecutionEngine()
    e.register_adapter(account_id, fake_adapter)
    return e


@pytest.fixture
def profit_lock_engine(execution_engine: ExecutionEngine) -> ProfitLockEngine:
    return ProfitLockEngine(execution_engine=execution_engine)


@pytest.fixture
async def enabled_lock(
    profit_lock_engine: ProfitLockEngine, account_id: uuid.UUID
) -> str:
    await profit_lock_engine.enable(
        instance_id="inst-1",
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        entry_price=Decimal("100"),
        quantity=Decimal("2"),
        side="long",
        trigger_percentage=Decimal("10"),
        trail_percentage=Decimal("5"),
    )
    return "inst-1"


class TestProfitLockEngineEnable:

    @pytest.mark.asyncio
    async def test_enable_creates_monitoring_state(
        self, profit_lock_engine: ProfitLockEngine, account_id: uuid.UUID
    ) -> None:
        result = await profit_lock_engine.enable(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            entry_price=Decimal("100"),
            quantity=Decimal("2"),
            side="long",
            trigger_percentage=Decimal("10"),
            trail_percentage=Decimal("5"),
        )
        assert result is True
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.MONITORING
        assert state.enabled is True
        assert state.trigger_percentage == Decimal("10")
        assert state.trail_percentage == Decimal("5")
        assert state.entry_price == Decimal("100")

    @pytest.mark.asyncio
    async def test_enable_invalid_trigger_raises(
        self, profit_lock_engine: ProfitLockEngine, account_id: uuid.UUID
    ) -> None:
        with pytest.raises(ValidationError):
            await profit_lock_engine.enable(
                instance_id="inst-1",
                exchange_account_id=account_id,
                symbol="BTCUSDT",
                entry_price=Decimal("100"),
                quantity=Decimal("2"),
                side="long",
                trigger_percentage=Decimal("0"),
                trail_percentage=Decimal("5"),
            )

    @pytest.mark.asyncio
    async def test_enable_invalid_trail_raises(
        self, profit_lock_engine: ProfitLockEngine, account_id: uuid.UUID
    ) -> None:
        with pytest.raises(ValidationError):
            await profit_lock_engine.enable(
                instance_id="inst-1",
                exchange_account_id=account_id,
                symbol="BTCUSDT",
                entry_price=Decimal("100"),
                quantity=Decimal("2"),
                side="long",
                trigger_percentage=Decimal("10"),
                trail_percentage=Decimal("100"),
            )


class TestProfitLockEnginePriceUpdate:

    @pytest.mark.asyncio
    async def test_price_update_triggers_lock(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        # Price goes to 112 → 12% profit, trigger at 10%
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.TRIGGERED
        assert state.is_triggered is True
        assert state.lock_price is not None
        assert state.highest_price == Decimal("112")

    @pytest.mark.asyncio
    async def test_price_update_no_trigger_below_threshold(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        await profit_lock_engine.on_price_update("inst-1", Decimal("105"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.MONITORING
        assert state.is_triggered is False

    @pytest.mark.asyncio
    async def test_price_update_trails_lock_upward(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        # Trigger at 112
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        state = await profit_lock_engine.get_state("inst-1")
        initial_lock = state.lock_price

        # Price goes higher → lock should trail up
        await profit_lock_engine.on_price_update("inst-1", Decimal("115"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.lock_price is not None
        assert state.lock_price > initial_lock
        assert state.highest_price == Decimal("115")

    @pytest.mark.asyncio
    async def test_price_update_executes_lock(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine, fake_adapter: FakeAdapter
    ) -> None:
        # Trigger
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        # Price drops below lock
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.EXECUTING
        assert state.lock_order_id is not None
        assert len(fake_adapter.place_calls) == 1
        assert fake_adapter.place_calls[0]["side"] == "sell"

    @pytest.mark.asyncio
    async def test_price_update_ignored_when_disabled(
        self, profit_lock_engine: ProfitLockEngine
    ) -> None:
        await profit_lock_engine.on_price_update("nonexistent", Decimal("120"))
        # Should not raise

    @pytest.mark.asyncio
    async def test_metrics_tracked(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        await profit_lock_engine.on_price_update("inst-1", Decimal("105"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        metrics = profit_lock_engine.get_metrics("inst-1")
        assert metrics.events_processed == 2
        assert metrics.decisions_made == 2
        assert metrics.locks_triggered == 1


class TestProfitLockEngineOrderEvents:

    @pytest.mark.asyncio
    async def test_order_filled_transitions_to_locked(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        # Trigger and execute
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))
        state = await profit_lock_engine.get_state("inst-1")
        order_id = state.lock_order_id

        # Simulate fill
        await profit_lock_engine.on_order_filled("inst-1", order_id, Decimal("100"), Decimal("2"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.LOCKED
        assert state.is_executed is True
        assert state.lock_order_id is None

        metrics = profit_lock_engine.get_metrics("inst-1")
        assert metrics.locks_executed == 1

    @pytest.mark.asyncio
    async def test_order_cancelled_resumes_trailing(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        # Trigger and execute
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))
        state = await profit_lock_engine.get_state("inst-1")
        order_id = state.lock_order_id

        # Simulate cancel
        await profit_lock_engine.on_order_cancelled("inst-1", order_id)
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.TRIGGERED
        assert state.lock_order_id is None

    @pytest.mark.asyncio
    async def test_order_filled_ignored_for_wrong_order(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))
        # Fill for wrong order_id
        await profit_lock_engine.on_order_filled("inst-1", "wrong_order", Decimal("100"), Decimal("2"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.EXECUTING  # unchanged


class TestProfitLockEngineDisable:

    @pytest.mark.asyncio
    async def test_disable_cancels_lock_order(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine, fake_adapter: FakeAdapter
    ) -> None:
        # Trigger and execute
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))

        result = await profit_lock_engine.disable("inst-1")
        assert result is True
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.DISABLED
        assert state.enabled is False
        assert len(fake_adapter.cancel_calls) == 1

    @pytest.mark.asyncio
    async def test_disable_nonexistent_raises(
        self, profit_lock_engine: ProfitLockEngine
    ) -> None:
        with pytest.raises(ProfitLockError):
            await profit_lock_engine.disable("nonexistent")


class TestProfitLockEnginePositionUpdate:

    @pytest.mark.asyncio
    async def test_position_update_changes_entry(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        await profit_lock_engine.on_position_update("inst-1", Decimal("95"), Decimal("3"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.entry_price == Decimal("95")
        assert state.quantity == Decimal("3")


class TestProfitLockEngineQueries:

    @pytest.mark.asyncio
    async def test_get_state_nonexistent_raises(
        self, profit_lock_engine: ProfitLockEngine
    ) -> None:
        with pytest.raises(ProfitLockError):
            await profit_lock_engine.get_state("nonexistent")

    @pytest.mark.asyncio
    async def test_get_metrics_returns_metrics(
        self, enabled_lock: str, profit_lock_engine: ProfitLockEngine
    ) -> None:
        metrics = profit_lock_engine.get_metrics("inst-1")
        assert metrics.events_processed == 0
        assert metrics.decisions_made == 0
