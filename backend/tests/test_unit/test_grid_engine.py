"""
Unit tests for GridEngine.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from core.exceptions import GridError
from core.types import GridLevelStatus, OrderResult, OrderSide, OrderStatus, OrderType
from engine.execution import ExecutionEngine
from engine.execution.models import OrderRequest
from engine.grid.calculator import GridCalculator
from engine.grid.engine import GridEngine
from engine.grid.planner import GridPlanner
from engine.grid.state import GridStateStore, GridStatus


class FakeAdapter:
    """Fake adapter for grid engine tests."""

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
def execution_engine(account_id: uuid.UUID) -> ExecutionEngine:
    e = ExecutionEngine()
    adapter = FakeAdapter()
    e.register_adapter(account_id, adapter)
    return e


@pytest.fixture
def grid_engine(execution_engine: ExecutionEngine) -> GridEngine:
    return GridEngine(execution_engine=execution_engine)


class TestGridEngineInitialize:

    @pytest.mark.asyncio
    async def test_initialize_grid_creates_levels(
        self, grid_engine: GridEngine, account_id: uuid.UUID
    ) -> None:
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
        assert len(state.levels) == 5
        assert state.upper_price == Decimal("100")
        assert state.lower_price == Decimal("50")
        assert state.symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_initialize_grid_all_levels_waiting(
        self, grid_engine: GridEngine, account_id: uuid.UUID
    ) -> None:
        state = await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=3,
            investment_per_grid=Decimal("100"),
        )
        for lv in state.levels:
            assert lv.status == GridLevelStatus.WAITING


class TestGridEngineActivate:

    @pytest.mark.asyncio
    async def test_activate_grid_places_buy_orders(
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
        result = await grid_engine.activate_grid("inst-1", Decimal("75"))
        assert result is True

        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.ACTIVE

        levels = await grid_engine.get_grid_levels("inst-1")
        open_levels = [lv for lv in levels if lv.status == GridLevelStatus.OPEN]
        assert len(open_levels) == 3  # levels 0,1,2 have buy_price < 75

    @pytest.mark.asyncio
    async def test_activate_grid_nonexistent_raises(
        self, grid_engine: GridEngine
    ) -> None:
        with pytest.raises(GridError):
            await grid_engine.activate_grid("nonexistent", Decimal("75"))


class TestGridEnginePause:

    @pytest.mark.asyncio
    async def test_pause_cancels_open_orders(
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
        result = await grid_engine.pause_grid("inst-1")
        assert result is True

        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.PAUSED

        levels = await grid_engine.get_grid_levels("inst-1")
        open_levels = [lv for lv in levels if lv.status == GridLevelStatus.OPEN]
        assert len(open_levels) == 0


class TestGridEngineResume:

    @pytest.mark.asyncio
    async def test_resume_replaces_orders(
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
        await grid_engine.pause_grid("inst-1")
        result = await grid_engine.resume_grid("inst-1", Decimal("75"))
        assert result is True

        state = await grid_engine.get_grid_state("inst-1")
        assert state.status == GridStatus.ACTIVE


class TestGridEnginePriceUpdate:

    @pytest.mark.asyncio
    async def test_price_update_places_new_buy(
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
        # Price drops to 48 — should trigger buy for level 0 (buy_price=50)
        await grid_engine.on_price_update("inst-1", Decimal("48"))

        levels = await grid_engine.get_grid_levels("inst-1")
        level_0 = [lv for lv in levels if lv.level == 0][0]
        assert level_0.status == GridLevelStatus.OPEN
        assert level_0.buy_order_id is not None

    @pytest.mark.asyncio
    async def test_price_update_ignored_when_paused(
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
        await grid_engine.pause_grid("inst-1")
        await grid_engine.on_price_update("inst-1", Decimal("48"))
        # Should not place any new orders
        levels = await grid_engine.get_grid_levels("inst-1")
        open_levels = [lv for lv in levels if lv.status == GridLevelStatus.OPEN]
        assert len(open_levels) == 0

    @pytest.mark.asyncio
    async def test_price_update_nonexistent_grid_no_error(
        self, grid_engine: GridEngine
    ) -> None:
        await grid_engine.on_price_update("nonexistent", Decimal("50"))


class TestGridEngineFillHandling:

    @pytest.mark.asyncio
    async def test_buy_filled_places_sell_order(
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

        # Simulate buy fill for level 0
        await grid_engine.on_buy_filled("inst-1", 0, Decimal("50"), Decimal("2"))

        levels = await grid_engine.get_grid_levels("inst-1")
        level_0 = [lv for lv in levels if lv.level == 0][0]
        assert level_0.status == GridLevelStatus.OPEN  # sell order placed
        assert level_0.sell_order_id is not None
        assert level_0.buy_order_id is None

    @pytest.mark.asyncio
    async def test_sell_filled_increments_cycles(
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
        await grid_engine.on_buy_filled("inst-1", 0, Decimal("50"), Decimal("2"))
        await grid_engine.on_sell_filled("inst-1", 0, Decimal("60"), Decimal("2"))

        state = await grid_engine.get_grid_state("inst-1")
        assert state.total_cycles == 1
        assert state.total_profit > 0

    @pytest.mark.asyncio
    async def test_sell_filled_resets_level_to_waiting(
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
        await grid_engine.on_buy_filled("inst-1", 0, Decimal("50"), Decimal("2"))
        await grid_engine.on_sell_filled("inst-1", 0, Decimal("60"), Decimal("2"))

        levels = await grid_engine.get_grid_levels("inst-1")
        level_0 = [lv for lv in levels if lv.level == 0][0]
        assert level_0.status == GridLevelStatus.WAITING

    @pytest.mark.asyncio
    async def test_buy_filled_nonexistent_level_raises(
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
        with pytest.raises(GridError):
            await grid_engine.on_buy_filled("inst-1", 99, Decimal("50"), Decimal("2"))


class TestGridEngineQueryMethods:

    @pytest.mark.asyncio
    async def test_get_grid_state_nonexistent_raises(
        self, grid_engine: GridEngine
    ) -> None:
        with pytest.raises(GridError):
            await grid_engine.get_grid_state("nonexistent")

    @pytest.mark.asyncio
    async def test_get_grid_level(
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
        lv = await grid_engine.get_grid_level("inst-1", 0)
        assert lv is not None
        assert lv.level == 0

    @pytest.mark.asyncio
    async def test_get_grid_level_nonexistent(
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
        assert await grid_engine.get_grid_level("inst-1", 99) is None

    @pytest.mark.asyncio
    async def test_get_grid_levels(
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
        levels = await grid_engine.get_grid_levels("inst-1")
        assert len(levels) == 5


class TestGridEngineCloseAll:

    @pytest.mark.asyncio
    async def test_close_all_cancels_open_orders(
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
        result = await grid_engine.close_all_grid_orders("inst-1")
        assert result is True

        levels = await grid_engine.get_grid_levels("inst-1")
        open_levels = [lv for lv in levels if lv.status == GridLevelStatus.OPEN]
        assert len(open_levels) == 0
