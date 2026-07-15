"""
Chaos tests for Recovery & Resilience (Layer 4).

Tests 5 failure scenarios:
1. Server restart → 100 instances recovered
2. Redis death → state rebuilt from PostgreSQL
3. WebSocket drop → reconnect + re-subscribe
4. Exchange timeout → queue + replay
5. Order filled during restart → detected on reconcile
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.types import GridLevel, GridLevelStatus, GridState, OrderResult, OrderStatus, PositionEntry
from engine.grid.persistence import GridPersistence
from engine.profit_lock.persistence import ProfitPersistence
from engine.profit_lock.state import ProfitLockState, ProfitLockStatus
from engine.recovery.connection import ConnectionRecovery, QueuedOrder
from engine.recovery.coordinator import InstanceContext, RecoveryCoordinator
from engine.recovery.persistence import RecoveryPersistence
from engine.recovery.reconciler import RuntimeReconciler
from engine.recovery.state import StateRecovery
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


class TestChaosServerRestart:
    """Scenario: Server restart → recover 100 Trading Processes."""

    @pytest.mark.asyncio
    async def test_recover_100_instances(self) -> None:
        cr = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )
        sr = StateRecovery(
            load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
        )
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)

        for i in range(100):
            coord.register_instance(f"inst-{i}", InstanceContext(
                instance_id=f"inst-{i}",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
            ))

        results = await coord.recover_all()
        assert len(results) == 100

        success_count = sum(
            1 for r in results.values()
            if r.connection_ok and r.state_ok and len(r.errors) == 0
        )
        assert success_count == 100
        assert coord.get_metrics()["recoveries_completed"] == 100

    @pytest.mark.asyncio
    async def test_no_duplicate_orders_after_restart(self) -> None:
        """Verify recovery is idempotent — running twice doesn't create duplicates."""
        cr = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )
        sr = StateRecovery(
            load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
        )
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)

        coord.register_instance("inst-1", InstanceContext(
            instance_id="inst-1", account_id="acc-1", exchange="binance", symbol="BTCUSDT",
        ))

        report1 = await coord.recover_instance("inst-1")
        assert report1.connection_ok is True

        report2 = await coord.recover_instance("inst-1")
        assert report2.connection_ok is True

        pm = sr.get_portfolio_manager()
        assert pm.get_open_position_count() == 0


class TestChaosRedisDeath:
    """Scenario: Redis dies → state rebuilt from PostgreSQL."""

    @pytest.mark.asyncio
    async def test_redis_down_then_recover(self) -> None:
        redis_alive = [False]

        def health() -> bool:
            return redis_alive[0]

        cr = ConnectionRecovery(redis_health_check=health)
        result = await cr.recover_redis()
        assert result is False

        redis_alive[0] = True
        result = await cr.recover_redis()
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_down_does_not_block_state_recovery(self) -> None:
        """Even with Redis down, state recovery from PostgreSQL should proceed."""
        cr = ConnectionRecovery(redis_health_check=lambda: False)
        sr = StateRecovery(
            load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
        )
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)

        coord.register_instance("inst-1", InstanceContext(
            instance_id="inst-1", account_id="acc-1", exchange="binance", symbol="BTCUSDT",
        ))
        report = await coord.recover_instance("inst-1")
        assert report.connection_ok is False
        assert report.state_ok is True
        assert len(report.errors) > 0
        assert any("Connection recovery" in e for e in report.errors)


class TestChaosWebSocketDrop:
    """Scenario: WebSocket drops → reconnect + re-subscribe."""

    @pytest.mark.asyncio
    async def test_disconnect_then_reconnect(self) -> None:
        resubscribed: list[tuple[str, list[str]]] = []

        def fake_resub(acc: str, syms: list[str]) -> bool:
            resubscribed.append((acc, syms))
            return True

        cr = ConnectionRecovery(resubscribe_fn=fake_resub)
        cr.register_subscriptions("acc-1", ["BTCUSDT", "ETHUSDT"])

        await cr.on_exchange_disconnect("binance", "acc-1")
        assert cr.is_exchange_connected("binance") is False

        await cr.on_exchange_reconnect("binance", "acc-1")
        assert cr.is_exchange_connected("binance") is True
        assert len(resubscribed) == 1
        assert resubscribed[0] == ("acc-1", ["BTCUSDT", "ETHUSDT"])
        assert cr.get_metrics()["exchange_reconnects"] == 1


class TestChaosExchangeTimeout:
    """Scenario: Exchange timeout → queue orders + replay on reconnect."""

    @pytest.mark.asyncio
    async def test_queue_and_replay(self) -> None:
        placed: list[QueuedOrder] = []

        def fake_place(order: QueuedOrder) -> str:
            placed.append(order)
            return f"executed-{order.instance_id}"

        cr = ConnectionRecovery(place_order_fn=fake_place)

        await cr.on_exchange_disconnect("binance", "acc-1")

        for i in range(5):
            cr.queue_order(QueuedOrder(
                instance_id=f"inst-{i}",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
                side="buy",
                quantity=Decimal("1"),
                price=Decimal("100"),
            ))

        assert cr.get_queue_size() == 5

        await cr.on_exchange_reconnect("binance", "acc-1")
        assert cr.get_queue_size() == 0
        assert len(placed) == 5
        assert cr.get_metrics()["orders_replayed"] == 5


class TestChaosOrderFilledDuringRestart:
    """Scenario: Order filled on exchange while server is down → detected on reconcile."""

    @pytest.mark.asyncio
    async def test_fill_detected_on_reconcile(self) -> None:
        grid = GridState(
            instance_id="inst-1",
            status="active",
            upper_price=Decimal("110"),
            lower_price=Decimal("90"),
            grid_count=10,
            grid_spacing=Decimal("2"),
            investment_per_grid=Decimal("100"),
            symbol="BTCUSDT",
            levels=[
                GridLevel(
                    level=0,
                    buy_price=Decimal("100"),
                    sell_price=Decimal("102"),
                    quantity=Decimal("1"),
                    buy_order_id="ord-buy-1",
                    status=GridLevelStatus.OPEN,
                ),
            ],
        )

        live_orders = [
            _make_order("ord-buy-1", status="filled", filled=Decimal("1")),
        ]

        reconciler = RuntimeReconciler()
        result = await reconciler.reconcile_grid("inst-1", grid, live_orders)

        assert result.action == "restored"
        assert grid.levels[0].status == GridLevelStatus.FILLED
        assert any("filled" in d.lower() for d in result.details)

    @pytest.mark.asyncio
    async def test_no_duplicate_order_after_fill(self) -> None:
        """After detecting fill, no new order should be placed for that level."""
        grid = GridState(
            instance_id="inst-1",
            status="active",
            upper_price=Decimal("110"),
            lower_price=Decimal("90"),
            grid_count=10,
            grid_spacing=Decimal("2"),
            investment_per_grid=Decimal("100"),
            symbol="BTCUSDT",
            levels=[
                GridLevel(
                    level=0,
                    buy_price=Decimal("100"),
                    sell_price=Decimal("102"),
                    quantity=Decimal("1"),
                    buy_order_id="ord-buy-1",
                    status=GridLevelStatus.OPEN,
                ),
            ],
        )

        live_orders = [
            _make_order("ord-buy-1", status="filled", filled=Decimal("1")),
        ]

        reconciler = RuntimeReconciler()
        await reconciler.reconcile_grid("inst-1", grid, live_orders)

        missing = reconciler.find_missing_orders(grid, live_orders)
        assert missing == []

    @pytest.mark.asyncio
    async def test_portfolio_reconciled_after_fill(self) -> None:
        """Portfolio should reflect the filled position after reconciliation."""
        pm = PortfolioManager()
        reconciler = RuntimeReconciler(portfolio=pm)

        exchange_positions = [
            PositionEntry(
                symbol="BTCUSDT",
                side="long",
                quantity=Decimal("1"),
                entry_price=Decimal("100"),
                unrealized_pnl=Decimal("5"),
            ),
        ]

        result = await reconciler.reconcile_portfolio("inst-1", [], exchange_positions)
        assert result.action == "restored"
        assert result.count == 1
        positions = pm.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "BTCUSDT"
        assert positions[0].quantity == Decimal("1")


class TestChaosFullRecoveryFlow:
    """Full end-to-end: server restart with grid + profit lock + portfolio."""

    @pytest.mark.asyncio
    async def test_full_recovery_with_all_components(self) -> None:
        grid_state = GridState(
            instance_id="inst-1",
            status="active",
            upper_price=Decimal("110"),
            lower_price=Decimal("90"),
            grid_count=10,
            grid_spacing=Decimal("2"),
            investment_per_grid=Decimal("100"),
            symbol="BTCUSDT",
            levels=[
                GridLevel(
                    level=0,
                    buy_price=Decimal("100"),
                    sell_price=Decimal("102"),
                    quantity=Decimal("1"),
                    buy_order_id="ord-1",
                    status=GridLevelStatus.OPEN,
                ),
            ],
        )
        grid_json = GridPersistence.to_json_string(grid_state)

        pl_state = ProfitLockState(
            instance_id="inst-1",
            status=ProfitLockStatus.MONITORING,
            enabled=True,
            trigger_percentage=Decimal("10"),
            trail_percentage=Decimal("5"),
            entry_price=Decimal("100"),
            quantity=Decimal("2"),
            side="long",
            highest_price=Decimal("112"),
            lock_price=None,
            is_triggered=False,
            is_executed=False,
            lock_order_id=None,
            exchange_account_id=None,
            symbol="BTCUSDT",
        )
        pl_json = ProfitPersistence.to_json_string(pl_state)

        exchange_positions = [
            PositionEntry(
                symbol="BTCUSDT",
                side="long",
                quantity=Decimal("2"),
                entry_price=Decimal("100"),
                unrealized_pnl=Decimal("20"),
            ),
        ]

        cr = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )
        sr = StateRecovery(
            load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
            load_grid_snapshot_fn=lambda iid: grid_json,
            load_profit_lock_snapshot_fn=lambda iid: pl_json,
            fetch_exchange_positions_fn=lambda iid: exchange_positions,
        )
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)

        coord.register_instance("inst-1", InstanceContext(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            has_grid=True,
            has_profit_lock=True,
        ))

        report = await coord.recover_instance("inst-1")

        assert report.connection_ok is True
        assert report.state_ok is True
        assert report.completed_at is not None
        assert len(report.reconciliation_results) >= 1

        status = coord.get_recovery_status("inst-1")
        assert status.state == "completed"

    @pytest.mark.asyncio
    async def test_independent_layer_failure(self) -> None:
        """If connection recovery fails, state and reconciliation should still proceed."""
        cr = ConnectionRecovery(
            redis_health_check=lambda: False,
            postgres_health_check=lambda: False,
        )
        sr = StateRecovery(
            load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
        )
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)

        coord.register_instance("inst-1", InstanceContext(
            instance_id="inst-1", account_id="acc-1", exchange="binance", symbol="BTCUSDT",
        ))

        report = await coord.recover_instance("inst-1")
        assert report.connection_ok is False
        assert report.state_ok is True
        assert report.reconciliation_ok is True
        assert any("Connection recovery" in e for e in report.errors)
