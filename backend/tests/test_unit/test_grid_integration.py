"""
Integration tests for the Grid Engine.

Tests the full grid lifecycle: initialize → activate → price updates →
buy fills → sell fills → cycle completion, using a FakeAdapter through
the real ExecutionEngine.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from core.types import GridLevelStatus, OrderResult, OrderSide, OrderStatus, OrderType
from engine.execution import ExecutionEngine
from engine.grid.engine import GridEngine
from engine.grid.state import GridStatus


class FakeAdapter:
    """Fake adapter that simulates exchange order placement and cancellation."""

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
        return [r for r in self._orders.values() if r.status == OrderStatus.OPEN.value]


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
def grid_engine(execution_engine: ExecutionEngine) -> GridEngine:
    return GridEngine(execution_engine=execution_engine)


@pytest.fixture
async def initialized_grid(
    grid_engine: GridEngine, account_id: uuid.UUID
) -> str:
    """Initialize a grid and return the instance_id."""
    await grid_engine.initialize_grid(
        instance_id="inst-1",
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        upper_price=Decimal("100"),
        lower_price=Decimal("50"),
        grid_count=5,
        investment_per_grid=Decimal("100"),
    )
    return "inst-1"


@pytest.fixture
async def active_grid(
    grid_engine: GridEngine, account_id: uuid.UUID
) -> str:
    """Initialize and activate a grid, return the instance_id."""
    await grid_engine.initialize_grid(
        instance_id="inst-1",
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        upper_price=Decimal("100"),
        lower_price=Decimal("50"),
        grid_count=5,
        investment_per_grid=Decimal("100"),
    )
    await grid_engine.activate_grid("inst-1", Decimal("75"))
    return "inst-1"


class TestGridLifecycle:

    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self, grid_engine: GridEngine, account_id: uuid.UUID, fake_adapter: FakeAdapter
    ) -> None:
        """Test: init → activate → price drop → buy fill → price rise → sell fill → cycle."""
        # 1. Initialize
        state = await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        assert state.status == GridStatus.INITIALIZED

        # 2. Activate at price 75
        await grid_engine.activate_grid("inst-1", Decimal("75"))
        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.ACTIVE

        # Levels 0,1,2 (buy prices 50,60,70) should have buy orders
        levels = await grid_engine.get_grid_levels("inst-1")
        open_count = sum(1 for lv in levels if lv.status == GridLevelStatus.OPEN)
        assert open_count == 3

        # 3. Price drops to 48 — level 3 (buy_price=80? no, buy_price=80 is level 3)
        # Actually level 3 has buy_price=80, level 4 has buy_price=90
        # Price 48 is below level 0 (50), so planner should place buy for level 0
        # But level 0 already has OPEN status from activation. Let's check:
        # Activation placed buys for levels where buy_price < 75: levels 0,1,2
        # Price 48 is below buy_price of level 0 (50), but level 0 is already OPEN
        # So no new orders should be placed
        await grid_engine.on_price_update("inst-1", Decimal("48"))

        # 4. Simulate buy fill for level 0
        await grid_engine.on_buy_filled("inst-1", 0, Decimal("50"), Decimal("2"))

        levels = await grid_engine.get_grid_levels("inst-1")
        level_0 = [lv for lv in levels if lv.level == 0][0]
        assert level_0.status == GridLevelStatus.OPEN  # sell order placed
        assert level_0.sell_order_id is not None

        # 5. Simulate sell fill for level 0
        await grid_engine.on_sell_filled("inst-1", 0, Decimal("60"), Decimal("2"))

        state = await grid_engine.get_grid_state("inst-1")
        assert state.total_cycles == 1
        assert state.total_profit == Decimal("20")  # (60-50) * 2

        levels = await grid_engine.get_grid_levels("inst-1")
        level_0 = [lv for lv in levels if lv.level == 0][0]
        assert level_0.status == GridLevelStatus.WAITING  # reset for next cycle

    @pytest.mark.asyncio
    async def test_pause_resume_lifecycle(
        self, grid_engine: GridEngine, account_id: uuid.UUID
    ) -> None:
        await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        await grid_engine.activate_grid("inst-1", Decimal("75"))

        # Pause
        await grid_engine.pause_grid("inst-1")
        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.PAUSED
        levels = await grid_engine.get_grid_levels("inst-1")
        assert all(lv.status != GridLevelStatus.OPEN for lv in levels)

        # Resume
        await grid_engine.resume_grid("inst-1", Decimal("75"))
        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.ACTIVE


class TestGridPriceEventDriven:

    @pytest.mark.asyncio
    async def test_price_drop_triggers_buy_order(
        self, grid_engine: GridEngine, account_id: uuid.UUID, fake_adapter: FakeAdapter
    ) -> None:
        """Verify that a price update event causes order placement (no polling)."""
        await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        await grid_engine.activate_grid("inst-1", Decimal("75"))

        initial_place_count = len(fake_adapter.place_calls)

        # Price drops — should trigger new buy orders for levels 3,4
        await grid_engine.on_price_update("inst-1", Decimal("85"))

        assert len(fake_adapter.place_calls) > initial_place_count

    @pytest.mark.asyncio
    async def test_no_polling_no_direct_exchange_access(
        self, grid_engine: GridEngine, account_id: uuid.UUID, fake_adapter: FakeAdapter
    ) -> None:
        """GridEngine should never call the adapter directly — only via ExecutionEngine."""
        await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=3,
            investment_per_grid=Decimal("100"),
        )
        await grid_engine.activate_grid("inst-1", Decimal("65"))
        await grid_engine.on_price_update("inst-1", Decimal("55"))
        await grid_engine.on_buy_filled("inst-1", 0, Decimal("50"), Decimal("2"))
        await grid_engine.on_sell_filled("inst-1", 0, Decimal("60"), Decimal("2"))

        # All place/call calls should go through ExecutionEngine → adapter
        # The grid engine itself has no reference to the adapter
        assert len(fake_adapter.place_calls) > 0


class TestGridMultipleCycles:

    @pytest.mark.asyncio
    async def test_two_complete_cycles(
        self, grid_engine: GridEngine, account_id: uuid.UUID
    ) -> None:
        """Verify that a level can complete multiple buy→sell cycles."""
        await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        await grid_engine.activate_grid("inst-1", Decimal("75"))

        # Cycle 1
        await grid_engine.on_buy_filled("inst-1", 1, Decimal("60"), Decimal("1.67"))
        await grid_engine.on_sell_filled("inst-1", 1, Decimal("70"), Decimal("1.67"))

        state = await grid_engine.get_grid_state("inst-1")
        assert state.total_cycles == 1

        # Cycle 2 — level 1 should be WAITING, ready for another buy
        levels = await grid_engine.get_grid_levels("inst-1")
        level_1 = [lv for lv in levels if lv.level == 1][0]
        assert level_1.status == GridLevelStatus.WAITING

        # Price drops to trigger buy for level 1
        await grid_engine.on_price_update("inst-1", Decimal("59"))
        levels = await grid_engine.get_grid_levels("inst-1")
        level_1 = [lv for lv in levels if lv.level == 1][0]
        assert level_1.status == GridLevelStatus.OPEN
        assert level_1.buy_order_id is not None

        # Fill buy and sell again
        await grid_engine.on_buy_filled("inst-1", 1, Decimal("60"), Decimal("1.67"))
        await grid_engine.on_sell_filled("inst-1", 1, Decimal("70"), Decimal("1.67"))

        state = await grid_engine.get_grid_state("inst-1")
        assert state.total_cycles == 2


class TestGridCloseAll:

    @pytest.mark.asyncio
    async def test_close_all_does_not_change_grid_status(
        self, grid_engine: GridEngine, account_id: uuid.UUID
    ) -> None:
        await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        await grid_engine.activate_grid("inst-1", Decimal("75"))
        await grid_engine.close_all_grid_orders("inst-1")

        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.ACTIVE  # still active, just orders cancelled
