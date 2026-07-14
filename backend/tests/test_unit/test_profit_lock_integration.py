"""
Integration tests for the Profit Lock Engine.

Tests the full profit lock lifecycle: enable → price rises → trigger →
trailing → price drops → execute → order filled → locked.
Also verifies independence from Grid Engine.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from core.types import OrderResult, OrderSide, OrderStatus, OrderType
from engine.execution import ExecutionEngine
from engine.profit_lock.engine import ProfitLockEngine
from engine.profit_lock.state import ProfitLockStatus


class FakeAdapter:
    """Fake adapter for profit lock integration tests."""

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


class TestProfitLockFullLifecycle:

    @pytest.mark.asyncio
    async def test_complete_lock_cycle(
        self,
        profit_lock_engine: ProfitLockEngine,
        account_id: uuid.UUID,
        fake_adapter: FakeAdapter,
    ) -> None:
        """Test: enable → price rises → trigger → trail → price drops → execute → fill → locked."""
        # 1. Enable profit lock
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
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.MONITORING

        # 2. Price rises to 112 → 12% profit, triggers lock
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.TRIGGERED
        assert state.lock_price is not None
        # lock = 112 * 0.95 = 106.4
        assert state.lock_price == Decimal("106.4")

        # 3. Price rises to 115 → lock trails up
        await profit_lock_engine.on_price_update("inst-1", Decimal("115"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.highest_price == Decimal("115")
        # lock = 115 * 0.95 = 109.25
        assert state.lock_price == Decimal("109.25")

        # 4. Price drops to 108 → below lock, execute
        await profit_lock_engine.on_price_update("inst-1", Decimal("108"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.EXECUTING
        assert state.lock_order_id is not None
        assert len(fake_adapter.place_calls) == 1
        assert fake_adapter.place_calls[0]["side"] == "sell"
        assert fake_adapter.place_calls[0]["price"] == Decimal("109.25")

        # 5. Order fills → locked
        order_id = state.lock_order_id
        await profit_lock_engine.on_order_filled("inst-1", order_id, Decimal("109.25"), Decimal("2"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.LOCKED
        assert state.is_executed is True

        # Verify metrics
        metrics = profit_lock_engine.get_metrics("inst-1")
        assert metrics.events_processed == 3  # 3 price updates
        assert metrics.locks_triggered == 1
        assert metrics.locks_executed == 1

    @pytest.mark.asyncio
    async def test_lock_cancelled_resumes_trailing(
        self,
        profit_lock_engine: ProfitLockEngine,
        account_id: uuid.UUID,
    ) -> None:
        """Test: trigger → execute → order cancelled → resume trailing → execute again."""
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

        # Trigger
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        # Execute
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.EXECUTING
        order_id = state.lock_order_id

        # Cancel
        await profit_lock_engine.on_order_cancelled("inst-1", order_id)
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.TRIGGERED

        # Price drops again → execute again
        await profit_lock_engine.on_price_update("inst-1", Decimal("100"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.EXECUTING
        assert state.lock_order_id is not None


class TestProfitLockShortPosition:

    @pytest.mark.asyncio
    async def test_short_position_lock(
        self,
        profit_lock_engine: ProfitLockEngine,
        account_id: uuid.UUID,
        fake_adapter: FakeAdapter,
    ) -> None:
        """Test profit lock for short position — price falling is profit."""
        await profit_lock_engine.enable(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            entry_price=Decimal("100"),
            quantity=Decimal("2"),
            side="short",
            trigger_percentage=Decimal("10"),
            trail_percentage=Decimal("5"),
        )

        # Price drops to 88 → 12% profit for short
        await profit_lock_engine.on_price_update("inst-1", Decimal("88"))
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.TRIGGERED
        assert state.is_triggered is True


class TestProfitLockIndependence:

    @pytest.mark.asyncio
    async def test_no_grid_engine_imports(self) -> None:
        """Verify profit_lock package does NOT import from grid engine."""
        import engine.profit_lock.engine as ple_module
        import sys

        # Check that no grid engine modules are in sys.modules from profit_lock import
        profit_lock_modules = [
            k for k in sys.modules if k.startswith("engine.profit_lock")
        ]
        grid_modules_loaded = [
            k for k in sys.modules if k.startswith("engine.grid")
        ]
        # Grid modules may be loaded from other tests, but profit_lock should not import them
        # Verify the engine module source doesn't import from engine.grid
        import inspect
        source = inspect.getsource(ple_module)
        # Check import lines only, not docstrings
        import_lines = [
            line.strip() for line in source.split("\n")
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "engine.grid" not in line, f"Profit lock engine imports from grid: {line}"
            assert "GridEngine" not in line, f"Profit lock engine imports GridEngine: {line}"

    @pytest.mark.asyncio
    async def test_no_exchange_adapter_access(
        self,
        profit_lock_engine: ProfitLockEngine,
        account_id: uuid.UUID,
        fake_adapter: FakeAdapter,
    ) -> None:
        """ProfitLockEngine should never call adapter directly — only via ExecutionEngine."""
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

        # Drive through full lifecycle
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("115"))
        await profit_lock_engine.on_price_update("inst-1", Decimal("108"))

        state = await profit_lock_engine.get_state("inst-1")
        order_id = state.lock_order_id
        await profit_lock_engine.on_order_filled("inst-1", order_id, Decimal("108"), Decimal("2"))

        # All place calls went through ExecutionEngine → adapter
        assert len(fake_adapter.place_calls) == 1
        # The profit lock engine itself has no reference to fake_adapter


class TestProfitLockDisable:

    @pytest.mark.asyncio
    async def test_disable_during_monitoring(
        self,
        profit_lock_engine: ProfitLockEngine,
        account_id: uuid.UUID,
    ) -> None:
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
        result = await profit_lock_engine.disable("inst-1")
        assert result is True
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.DISABLED
        assert state.enabled is False

    @pytest.mark.asyncio
    async def test_disable_during_triggered(
        self,
        profit_lock_engine: ProfitLockEngine,
        account_id: uuid.UUID,
    ) -> None:
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
        await profit_lock_engine.on_price_update("inst-1", Decimal("112"))
        result = await profit_lock_engine.disable("inst-1")
        assert result is True
        state = await profit_lock_engine.get_state("inst-1")
        assert state.status == ProfitLockStatus.DISABLED
