"""
Unit tests for RuntimeReconciler (Layer 3).
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.types import GridLevel, GridLevelStatus, GridState, OrderResult, OrderStatus, PositionEntry
from engine.recovery.reconciler import ReconciliationResult, RuntimeReconciler
from engine.risk.portfolio import PortfolioManager


def _make_order(
    order_id: str,
    symbol: str = "BTCUSDT",
    side: str = "buy",
    status: str = "open",
    filled: Decimal = Decimal("0"),
) -> OrderResult:
    return OrderResult(
        order_id=order_id,
        exchange_order_id=order_id,
        symbol=symbol,
        side=side,
        order_type="limit",
        quantity=Decimal("1"),
        price=Decimal("100"),
        filled_quantity=filled,
        average_fill_price=Decimal("100") if filled > 0 else None,
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_grid_state(levels: list[GridLevel] | None = None) -> GridState:
    return GridState(
        instance_id="inst-1",
        status="active",
        upper_price=Decimal("110"),
        lower_price=Decimal("90"),
        grid_count=10,
        grid_spacing=Decimal("2"),
        investment_per_grid=Decimal("100"),
        symbol="BTCUSDT",
        levels=levels or [
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"), quantity=Decimal("1")),
            GridLevel(level=1, buy_price=Decimal("98"), sell_price=Decimal("100"), quantity=Decimal("1")),
        ],
    )


class TestFindMissingOrders:

    def test_no_missing_when_all_present(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), buy_order_id="ord-1", status=GridLevelStatus.OPEN),
        ])
        live = [_make_order("ord-1")]
        missing = reconciler.find_missing_orders(grid, live)
        assert missing == []

    def test_missing_when_order_not_on_exchange(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), buy_order_id="ord-1", status=GridLevelStatus.OPEN),
        ])
        live: list[OrderResult] = []
        missing = reconciler.find_missing_orders(grid, live)
        assert len(missing) == 1
        assert missing[0].level == 0

    def test_no_missing_for_waiting_levels(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), status=GridLevelStatus.WAITING),
        ])
        live: list[OrderResult] = []
        missing = reconciler.find_missing_orders(grid, live)
        assert missing == []


class TestFindOrphanOrders:

    def test_no_orphans_when_all_tracked(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), buy_order_id="ord-1", status=GridLevelStatus.OPEN),
        ])
        live = [_make_order("ord-1")]
        orphans = reconciler.find_orphan_orders(grid, live)
        assert orphans == []

    def test_orphan_when_order_not_in_local(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state()
        live = [_make_order("unknown-order")]
        orphans = reconciler.find_orphan_orders(grid, live)
        assert len(orphans) == 1
        assert orphans[0].exchange_order_id == "unknown-order"

    def test_no_orphans_for_filled_orders(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state()
        live = [_make_order("unknown", status="filled")]
        orphans = reconciler.find_orphan_orders(grid, live)
        assert orphans == []


class TestReconcileGrid:

    @pytest.mark.asyncio
    async def test_reconcile_filled_on_exchange(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), buy_order_id="ord-1", status=GridLevelStatus.OPEN),
        ])
        live = [_make_order("ord-1", status="filled", filled=Decimal("1"))]
        result = await reconciler.reconcile_grid("inst-1", grid, live)
        assert result.component == "grid"
        assert result.action == "restored"
        assert grid.levels[0].status == GridLevelStatus.FILLED

    @pytest.mark.asyncio
    async def test_reconcile_cancelled_on_exchange(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), buy_order_id="ord-1", status=GridLevelStatus.OPEN),
        ])
        live = [_make_order("ord-1", status="cancelled")]
        result = await reconciler.reconcile_grid("inst-1", grid, live)
        assert result.action == "restored"
        assert grid.levels[0].status == GridLevelStatus.WAITING
        assert grid.levels[0].buy_order_id is None

    @pytest.mark.asyncio
    async def test_reconcile_no_changes(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state([
            GridLevel(level=0, buy_price=Decimal("100"), sell_price=Decimal("102"),
                      quantity=Decimal("1"), buy_order_id="ord-1", status=GridLevelStatus.OPEN),
        ])
        live = [_make_order("ord-1", status="open")]
        result = await reconciler.reconcile_grid("inst-1", grid, live)
        assert result.action == "skipped"

    @pytest.mark.asyncio
    async def test_reconcile_with_orphans(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state()
        live = [_make_order("orphan-1")]
        result = await reconciler.reconcile_grid("inst-1", grid, live)
        assert any("orphan" in d.lower() for d in result.details)


class TestReconcilePortfolio:

    @pytest.mark.asyncio
    async def test_add_missing_position(self) -> None:
        pm = PortfolioManager()
        reconciler = RuntimeReconciler(portfolio=pm)
        exchange_positions = [
            PositionEntry(
                symbol="BTCUSDT", side="long", quantity=Decimal("2"),
                entry_price=Decimal("100"), unrealized_pnl=Decimal("0"),
            ),
        ]
        result = await reconciler.reconcile_portfolio("inst-1", [], exchange_positions)
        assert result.action == "restored"
        assert result.count == 1
        assert len(pm.get_positions()) == 1

    @pytest.mark.asyncio
    async def test_close_stale_position(self) -> None:
        pm = PortfolioManager()
        pm.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("2"),
        )
        reconciler = RuntimeReconciler(portfolio=pm)
        result = await reconciler.reconcile_portfolio("inst-1", pm.get_positions(), [])
        assert result.action == "restored"
        assert result.count == 1
        assert pm.get_open_position_count() == 0

    @pytest.mark.asyncio
    async def test_no_changes_when_in_sync(self) -> None:
        pm = PortfolioManager()
        pm.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("2"),
        )
        reconciler = RuntimeReconciler(portfolio=pm)
        exchange_positions = [
            PositionEntry(
                symbol="BTCUSDT", side="long", quantity=Decimal("2"),
                entry_price=Decimal("100"), unrealized_pnl=Decimal("0"),
            ),
        ]
        result = await reconciler.reconcile_portfolio(
            "inst-1", pm.get_positions(), exchange_positions
        )
        assert result.action == "skipped"
        assert result.count == 0


class TestReconcilerMetrics:

    @pytest.mark.asyncio
    async def test_metrics_tracked(self) -> None:
        reconciler = RuntimeReconciler()
        grid = _make_grid_state()
        await reconciler.reconcile_grid("inst-1", grid, [])
        await reconciler.reconcile_portfolio("inst-1", [], [])
        metrics = reconciler.get_metrics()
        assert metrics["grid_reconciliations"] == 1
        assert metrics["portfolio_reconciliations"] == 1
