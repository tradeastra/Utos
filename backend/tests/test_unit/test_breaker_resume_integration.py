"""
Integration tests for the circuit breaker resume modes.

End-to-end test: configure a grid + breaker → trigger the breaker with a
price drop → verify that each of the 3 resume modes (TA_CONFIRM, WIDEN_STEP,
TRAILING_BUY) produces DIFFERENT behavior in the grid engine's buy/skip
decisions on subsequent price updates.

Grid setup:
  - BTCUSDT, upper=100, lower=80, 5 levels → buy prices 80, 84, 88, 92, 96.
  - Activate at price=80 → no initial buys (80 > 80 is False for plan_initial),
    so ALL levels stay WAITING. This lets us observe clean buy decisions
    after the breaker triggers, without leftover OPEN levels from activation.
  - Breaker: threshold=4%, day_open=100 → triggers when price <= 96.

Three scenarios:
  1. TA_CONFIRM: buys BLOCKED until TA 15m passes (no 15m candles → stays blocked).
  2. WIDEN_STEP: buys PROCEED but only at every 2nd level (0,2,4) — wider spacing.
  3. TRAILING_BUY: buys BLOCKED until price recovers 5% from the intraday low.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from core.domain_types import OrderResult, OrderStatus
from engine.execution import ExecutionEngine
from engine.grid.circuit_breaker import BreakerResumeMode
from engine.grid.engine import GridEngine


class FakeAdapter:
    """Fake adapter that records all place_order calls for assertion."""

    def __init__(self, name: str = "binance") -> None:
        self.exchange_name = name
        self.place_calls: list[dict[str, Any]] = []
        self.cancel_calls: list[dict[str, Any]] = []
        self._orders: dict[str, OrderResult] = {}
        self._counter = 0

    async def place_order(
        self, symbol, side, order_type, quantity, price=None,
        stop_price=None, client_order_id=None,
    ) -> OrderResult:
        self.place_calls.append({
            "symbol": symbol, "side": side, "price": price, "quantity": quantity,
        })
        self._counter += 1
        order_id = f"ex_{self._counter}"
        result = OrderResult(
            order_id=f"local_{order_id}", exchange_order_id=order_id,
            symbol=symbol.upper(), side=side, order_type=order_type,
            quantity=quantity, price=price, filled_quantity=Decimal("0"),
            average_fill_price=None, status=OrderStatus.OPEN.value,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        self._orders[order_id] = result
        return result

    async def cancel_order(self, symbol, order_id) -> bool:
        self.cancel_calls.append({"symbol": symbol, "order_id": order_id})
        return True

    async def get_order(self, symbol, order_id) -> OrderResult:
        return self._orders.get(order_id)

    async def get_open_orders(self, symbol=None) -> list[OrderResult]:
        return [r for r in self._orders.values() if r.status == OrderStatus.OPEN.value]


@pytest.fixture
def account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def execution_engine(account_id, fake_adapter) -> ExecutionEngine:
    e = ExecutionEngine()
    e.register_adapter(account_id, fake_adapter)
    return e


@pytest.fixture
def grid_engine(execution_engine) -> GridEngine:
    return GridEngine(execution_engine=execution_engine)


def _buy_prices_from_place_calls(adapter: FakeAdapter) -> list[Decimal]:
    """Extract buy prices from the adapter's recorded place_order calls."""
    return [
        c["price"] for c in adapter.place_calls
        if c["side"] == "buy" and c["price"] is not None
    ]


class TestBreakerResumeModesIntegration:
    """End-to-end: trigger breaker → verify 3 modes behave differently.

    Grid: upper=100, lower=80, 5 levels → buy prices 80, 84, 88, 92, 96.
    Activate at 80 → no initial buys (all levels stay WAITING).
    Breaker: threshold=4%, day_open=100 → triggers at price <= 96.
    """

    @pytest.fixture
    async def active_grid(self, grid_engine, account_id) -> str:
        """Initialize + activate a grid. Activate at lower_price=80 so no
        initial buys are placed (plan_initial uses strict > comparison).
        All 5 levels stay WAITING → clean slate for breaker tests.
        """
        await grid_engine.initialize_grid(
            instance_id="inst-1",
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            upper_price=Decimal("100"),
            lower_price=Decimal("80"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        await grid_engine.activate_grid("inst-1", Decimal("80"))
        return "inst-1"

    @pytest.mark.asyncio
    async def test_ta_confirm_blocks_all_buys_after_trigger(
        self, grid_engine: GridEngine, fake_adapter: FakeAdapter,
        active_grid: str,
    ) -> None:
        """TA_CONFIRM: after trigger, ALL buys are blocked (no 15m candles
        available → TA gate never passes → buys stay blocked indefinitely).
        """
        grid_engine.configure_circuit_breaker(
            instance_id="inst-1",
            critical_threshold=Decimal("4.0"),
            resume_mode=BreakerResumeMode.TA_CONFIRM,
            day_open_price=Decimal("100"),
        )
        fake_adapter.place_calls.clear()

        # Price drops to 95 → drop 5% > 4% threshold → breaker triggers.
        await grid_engine.on_price_update("inst-1", Decimal("95"))
        breaker = grid_engine.get_circuit_breaker("inst-1")
        assert breaker is not None
        assert breaker.triggered is True
        # No buys placed this tick (breaker just triggered → cancel + skip).
        buys = _buy_prices_from_place_calls(fake_adapter)
        assert buys == []

        # Price falls to 80 → all levels have buy_price >= 80, so without
        # the breaker all 5 would get buys. With TA_CONFIRM: all blocked.
        await grid_engine.on_price_update("inst-1", Decimal("80"))
        buys = _buy_prices_from_place_calls(fake_adapter)
        assert buys == []

        # Price falls further to 78 (below lower_price) → still blocked.
        await grid_engine.on_price_update("inst-1", Decimal("78"))
        buys = _buy_prices_from_place_calls(fake_adapter)
        assert buys == []

    @pytest.mark.asyncio
    async def test_widen_step_places_buys_at_every_2nd_level(
        self, grid_engine: GridEngine, fake_adapter: FakeAdapter,
        active_grid: str,
    ) -> None:
        """WIDEN_STEP: after trigger, buys PROCEED but only at every 2nd level.
        At price 80: levels 0,1,2,3,4 all qualify (buy_price >= 80).
        With multiplier 2: only levels 0,2,4 (buy 80,88,96) get buys.
        Levels 1,3 (buy 84,92) are SKIPPED.
        """
        grid_engine.configure_circuit_breaker(
            instance_id="inst-1",
            critical_threshold=Decimal("4.0"),
            resume_mode=BreakerResumeMode.WIDEN_STEP,
            widen_multiplier=Decimal("2"),
            day_open_price=Decimal("100"),
        )
        fake_adapter.place_calls.clear()

        # Trigger at 95 (drop 5%).
        await grid_engine.on_price_update("inst-1", Decimal("95"))
        breaker = grid_engine.get_circuit_breaker("inst-1")
        assert breaker.triggered is True

        # Price falls to 80 → all 5 levels qualify (buy_price >= 80).
        # WIDEN_STEP 2x: only levels 0,2,4 (buy 80,88,96) get buys.
        await grid_engine.on_price_update("inst-1", Decimal("80"))
        buys = _buy_prices_from_place_calls(fake_adapter)
        # Levels 0,2,4 placed; 1,3 skipped.
        assert Decimal("80") in buys  # level 0 (0 % 2 == 0)
        assert Decimal("88") in buys  # level 2 (2 % 2 == 0)
        assert Decimal("96") in buys  # level 4 (4 % 2 == 0)
        assert Decimal("84") not in buys  # level 1 skipped (1 % 2 != 0)
        assert Decimal("92") not in buys  # level 3 skipped (3 % 2 != 0)
        # Exactly 3 buys (not 5).
        assert len(buys) == 3

    @pytest.mark.asyncio
    async def test_trailing_buy_blocks_until_recovery(
        self, grid_engine: GridEngine, fake_adapter: FakeAdapter,
        active_grid: str,
    ) -> None:
        """TRAILING_BUY: after trigger, buys BLOCKED until price recovers 5%
        from the intraday low. After recovery, breaker resets (triggered=False)
        and buys resume normally on the next price drop.
        """
        grid_engine.configure_circuit_breaker(
            instance_id="inst-1",
            critical_threshold=Decimal("4.0"),
            resume_mode=BreakerResumeMode.TRAILING_BUY,
            recovery_pct=Decimal("5.0"),
            day_open_price=Decimal("100"),
        )
        fake_adapter.place_calls.clear()

        # Trigger at 95 (drop 5%). bottom_price seeded at 95.
        await grid_engine.on_price_update("inst-1", Decimal("95"))
        breaker = grid_engine.get_circuit_breaker("inst-1")
        assert breaker.triggered is True
        assert breaker.bottom_price == Decimal("95")

        # Price falls to 90 → bottom updates to 90. Still blocked.
        await grid_engine.on_price_update("inst-1", Decimal("90"))
        assert breaker.bottom_price == Decimal("90")
        buys = _buy_prices_from_place_calls(fake_adapter)
        assert buys == []

        # Price recovers to 92 → recovery from 90 = 2.2% < 5% → still blocked.
        await grid_engine.on_price_update("inst-1", Decimal("92"))
        buys = _buy_prices_from_place_calls(fake_adapter)
        assert buys == []
        assert breaker.triggered is True

        # Price recovers to 94.5 → recovery from 90 = 5% → RESUME.
        # 90 × 1.05 = 94.5 → should_resume_trailing returns True.
        await grid_engine.on_price_update("inst-1", Decimal("94.5"))
        assert breaker.triggered is False  # reset by trailing recovery
        # At price 94.5, level 4 (buy=96) qualifies: 94.5 <= 96 → place_buy.
        # After reset, no widen → buy placed normally. This proves the grid
        # is buying again (breaker no longer blocking).
        buys = _buy_prices_from_place_calls(fake_adapter)
        assert Decimal("96") in buys  # level 4 placed after recovery

        # Note: dropping price further (e.g. to 80) would RE-TRIGGER the breaker
        # (drop from day_open=100 > 4% threshold), so we don't test that here.
        # The key assertion is that recovery resets the breaker and allows
        # a buy — proving TRAILING_BUY unblocks on recovery.

    @pytest.mark.asyncio
    async def test_three_modes_produce_different_buy_counts(
        self, grid_engine: GridEngine, fake_adapter: FakeAdapter,
        active_grid: str,
    ) -> None:
        """Smoke test: run the same price sequence with each of the 3 modes and
        verify they produce DIFFERENT numbers of buy orders — proving the
        modes are not no-ops and diverge from each other.

        Price sequence: trigger at 95, then fall to 80 (all levels qualify).
        """
        prices = [Decimal("95"), Decimal("80")]

        async def run_mode(mode: BreakerResumeMode, **kw) -> int:
            fake_adapter.place_calls.clear()
            grid_engine.configure_circuit_breaker(
                instance_id="inst-1",
                critical_threshold=Decimal("4.0"),
                resume_mode=mode,
                day_open_price=Decimal("100"),
                **kw,
            )
            for p in prices:
                await grid_engine.on_price_update("inst-1", p)
            return len(_buy_prices_from_place_calls(fake_adapter))

        ta_count = await run_mode(BreakerResumeMode.TA_CONFIRM)
        widen_count = await run_mode(
            BreakerResumeMode.WIDEN_STEP, widen_multiplier=Decimal("2")
        )
        trailing_count = await run_mode(
            BreakerResumeMode.TRAILING_BUY, recovery_pct=Decimal("5.0")
        )

        # TA_CONFIRM: 0 buys (all blocked, no 15m candles).
        assert ta_count == 0
        # WIDEN_STEP: 3 buys (levels 0,2,4 only — every 2nd level).
        assert widen_count == 3
        # TRAILING_BUY: 0 buys (price 80 never recovers 5% from low 80).
        # At price 80, bottom=80, recovery 0% < 5% → still blocked.
        assert trailing_count == 0
        # The 3 modes diverge: WIDEN_STEP places buys, the other two don't.
        assert widen_count != ta_count
        assert widen_count != trailing_count
