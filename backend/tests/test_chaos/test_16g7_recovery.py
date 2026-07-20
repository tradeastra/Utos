"""
16G-7: Recovery Verification Tests

After every chaos test, automatically run:
  RecoveryCoordinator → StateRecovery → RuntimeReconciler → Portfolio → Risk → Grid → ProfitLock

Verifies:
- No duplicate orders
- No orphan orders
- Positions match exchange
- PnL consistent
- Exposure consistent
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from core.domain_types import (
    GridLevel,
    GridLevelStatus,
    GridState,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionEntry,
)
from engine.execution.models import OrderRequest
from engine.grid.state import GridStatus
from engine.recovery.connection import ConnectionRecovery, QueuedOrder
from engine.recovery.coordinator import (
    InstanceContext,
    RecoveryCoordinator,
)
from engine.recovery.persistence import RecoveryPersistence
from engine.recovery.reconciler import RuntimeReconciler
from engine.recovery.state import StateRecovery
from engine.risk.exposure import ExposureManager
from engine.risk.manager import RiskLimits, RiskManager
from engine.risk.portfolio import PortfolioManager, Position
from tests.test_chaos.chaos_adapter import ChaosExchangeAdapter


class TestRecoveryNoDuplicateOrders:
    """Verify no duplicate orders after recovery."""

    @pytest.mark.asyncio
    async def test_no_duplicate_after_recovery(self):
        """After recovery, no duplicate orders should exist in tracker."""
        from engine.execution.execution_engine import ExecutionEngine
        from engine.execution.executor import OrderExecutor
        from engine.execution.tracker import OrderTracker
        from engine.execution.validator import OrderValidator

        adapter = ChaosExchangeAdapter()
        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=3, base_delay=0.01)
        engine = ExecutionEngine(
            validator=validator, executor=executor, tracker=tracker
        )

        account_id = uuid.uuid4()
        engine.register_adapter(account_id, adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        # Place order
        result1 = await engine.place_order(request)

        # Simulate recovery: try same request again
        result2 = await engine.place_order(request)

        # Should return same order (idempotent)
        assert result1.exchange_order_id == result2.exchange_order_id

    @pytest.mark.asyncio
    async def test_no_duplicate_after_reconnect(self):
        """After exchange reconnect, queued orders should not duplicate existing ones."""
        place_count = 0

        def place_order_fn(order):
            nonlocal place_count
            place_count += 1
            return {"status": "ok", "order_id": f"order-{place_count}"}

        recovery = ConnectionRecovery(place_order_fn=place_order_fn)

        # Queue one order
        recovery.queue_order(
            QueuedOrder(
                instance_id="inst-1",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
                side="buy",
                quantity=Decimal("0.1"),
                price=Decimal("45000"),
            )
        )

        # Replay once
        await recovery.replay_queued_orders()
        assert place_count == 1

        # Replay again — should be empty queue
        await recovery.replay_queued_orders()
        assert place_count == 1  # No duplicate


class TestRecoveryNoOrphanOrders:
    """Verify no orphan orders after recovery."""

    @pytest.mark.asyncio
    async def test_orphan_detection(self):
        """Reconciler should detect orphan orders (on exchange but not in local state)."""
        reconciler = RuntimeReconciler()

        levels = [
            GridLevel(
                level=0,
                buy_price=Decimal("49000"),
                sell_price=Decimal("50000"),
                quantity=Decimal("0.1"),
                status=GridLevelStatus.WAITING,
            ),
        ]

        state = GridState(
            instance_id="inst-1",
            status=GridStatus.ACTIVE,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=1,
            grid_spacing=Decimal("1000"),
            investment_per_grid=Decimal("100"),
            levels=levels,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )

        # Exchange has an order that local state doesn't know about
        live_orders = [
            OrderResult(
                order_id="orphan-1",
                exchange_order_id="orphan-1",
                symbol="BTCUSDT",
                side="buy",
                order_type="limit",
                status=OrderStatus.OPEN.value,
                quantity=Decimal("0.1"),
                price=Decimal("48000"),
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            ),
        ]

        orphans = reconciler.find_orphan_orders(state, live_orders)
        assert len(orphans) == 1
        assert orphans[0].exchange_order_id == "orphan-1"

    @pytest.mark.asyncio
    async def test_missing_order_detection(self):
        """Reconciler should detect missing orders (in local state but not on exchange)."""
        reconciler = RuntimeReconciler()

        levels = [
            GridLevel(
                level=0,
                buy_price=Decimal("49000"),
                sell_price=Decimal("50000"),
                quantity=Decimal("0.1"),
                status=GridLevelStatus.OPEN,
                buy_order_id="local-order-1",
            ),
        ]

        state = GridState(
            instance_id="inst-1",
            status=GridStatus.ACTIVE,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=1,
            grid_spacing=Decimal("1000"),
            investment_per_grid=Decimal("100"),
            levels=levels,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )

        # Exchange doesn't have local-order-1
        live_orders = []

        missing = reconciler.find_missing_orders(state, live_orders)
        assert len(missing) == 1
        assert missing[0].buy_order_id == "local-order-1"


class TestRecoveryPositionConsistency:
    """Verify positions match exchange after recovery."""

    @pytest.mark.asyncio
    async def test_portfolio_reconciliation_adds_missing(self):
        """Positions on exchange but not locally should be added."""
        portfolio = PortfolioManager()
        reconciler = RuntimeReconciler(portfolio=portfolio)

        # Local has no positions
        local_positions: list[Position] = []

        # Exchange has a position
        exchange_positions = [
            PositionEntry(
                symbol="BTCUSDT",
                side="long",
                quantity=Decimal("0.5"),
                entry_price=Decimal("45000"),
                unrealized_pnl=Decimal("500"),
            ),
        ]

        result = await reconciler.reconcile_portfolio(
            "inst-1", local_positions, exchange_positions
        )

        assert result.action == "restored"
        assert result.count == 1
        assert "BTCUSDT" in [d for d in result.details if "BTCUSDT" in d][0]

    @pytest.mark.asyncio
    async def test_portfolio_reconciliation_closes_stale(self):
        """Positions locally but not on exchange should be closed."""
        portfolio = PortfolioManager()
        portfolio.register_position(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="long",
            entry_price=Decimal("45000"),
            quantity=Decimal("0.5"),
        )

        reconciler = RuntimeReconciler(portfolio=portfolio)

        local_positions = portfolio.get_positions()
        exchange_positions: list[PositionEntry] = []  # Exchange has no positions

        result = await reconciler.reconcile_portfolio(
            "inst-1", local_positions, exchange_positions
        )

        assert result.action == "restored"
        assert result.count == 1


class TestRecoveryPnLConsistency:
    """Verify PnL is consistent after recovery."""

    @pytest.mark.asyncio
    async def test_pnl_calculated_after_recovery(self):
        """PnL should be correctly calculated after position recovery."""
        from engine.profit_lock.calculator import ProfitCalculator

        calc = ProfitCalculator()

        # Long position: entry 45000, current 46000
        result = calc.calculate(
            entry_price=Decimal("45000"),
            current_price=Decimal("46000"),
            quantity=Decimal("0.5"),
            side="long",
        )

        assert result.is_profitable is True
        assert result.profit_percentage > Decimal("0")
        assert result.floating_profit > Decimal("0")

    @pytest.mark.asyncio
    async def test_pnl_negative_for_losing_position(self):
        """PnL should be negative for losing position."""
        from engine.profit_lock.calculator import ProfitCalculator

        calc = ProfitCalculator()

        result = calc.calculate(
            entry_price=Decimal("50000"),
            current_price=Decimal("45000"),
            quantity=Decimal("0.5"),
            side="long",
        )

        assert result.is_profitable is False
        assert result.floating_profit < Decimal("0")


class TestRecoveryExposureConsistency:
    """Verify exposure is consistent after recovery."""

    @pytest.mark.asyncio
    async def test_exposure_after_position_recovery(self):
        """Exposure should reflect recovered positions."""
        portfolio = PortfolioManager()
        exposure_mgr = ExposureManager()

        # Register a position
        portfolio.register_position(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="long",
            entry_price=Decimal("45000"),
            quantity=Decimal("0.5"),
        )

        prices = {"BTCUSDT": Decimal("46000")}
        positions = portfolio.get_positions()

        report = exposure_mgr.calculate_exposure(positions, prices)

        # Exposure should be 0.5 * 46000 = 23000
        assert report.total_exposure == Decimal("23000")

    @pytest.mark.asyncio
    async def test_risk_check_after_recovery(self):
        """Risk check should work with recovered positions."""
        portfolio = PortfolioManager()
        exposure_mgr = ExposureManager()
        risk_mgr = RiskManager(portfolio, exposure_mgr)

        risk_mgr.set_risk_parameters(
            "user1",
            RiskLimits(
                max_position_size=Decimal("100000"),
                max_capital_per_instance=Decimal("50000"),
                max_exposure_per_symbol=Decimal("200000"),
                max_exposure_per_exchange=Decimal("500000"),
                max_open_positions=10,
            ),
        )

        # Register recovered position
        portfolio.register_position(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="long",
            entry_price=Decimal("45000"),
            quantity=Decimal("0.5"),
        )

        risk_mgr.on_price_update("user1", "BTCUSDT", Decimal("46000"))

        # Check risk — should pass
        result = risk_mgr.check_order_risk(
            instance_id="inst-2",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("46000"),
            user_id="user1",
        )

        assert result.allowed is True


class TestFullRecoveryFlow:
    """Full recovery flow: Coordinator → State → Reconciler → Portfolio → Risk."""

    @pytest.mark.asyncio
    async def test_full_recovery_coordinator(self):
        """RecoveryCoordinator should execute full recovery without errors."""
        # Setup all layers
        connection_recovery = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )

        state_recovery = StateRecovery(
            load_instance_fn=lambda iid: {"status": "active", "instance_id": iid},
            load_grid_snapshot_fn=lambda iid: None,
            load_profit_lock_snapshot_fn=lambda iid: None,
            fetch_exchange_positions_fn=lambda iid: [],
        )

        reconciler = RuntimeReconciler()
        persistence = RecoveryPersistence()

        coordinator = RecoveryCoordinator(
            connection_recovery=connection_recovery,
            state_recovery=state_recovery,
            reconciler=reconciler,
            persistence=persistence,
        )

        # Register instance
        coordinator.register_instance(
            "inst-1",
            InstanceContext(
                instance_id="inst-1",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
                has_grid=False,
                has_profit_lock=False,
            ),
        )

        # Execute recovery
        report = await coordinator.recover_instance("inst-1")

        assert report.connection_ok is True
        assert report.state_ok is True
        assert report.reconciliation_ok is True
        assert len(report.errors) == 0

    @pytest.mark.asyncio
    async def test_full_recovery_with_grid(self):
        """Full recovery including grid state."""
        connection_recovery = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )

        state_recovery = StateRecovery(
            load_instance_fn=lambda iid: {"status": "active"},
            load_grid_snapshot_fn=lambda iid: None,  # No snapshot
            load_profit_lock_snapshot_fn=lambda iid: None,
            fetch_exchange_positions_fn=lambda iid: [],
        )

        reconciler = RuntimeReconciler()
        persistence = RecoveryPersistence()

        coordinator = RecoveryCoordinator(
            connection_recovery=connection_recovery,
            state_recovery=state_recovery,
            reconciler=reconciler,
            persistence=persistence,
        )

        coordinator.register_instance(
            "inst-grid",
            InstanceContext(
                instance_id="inst-grid",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
                has_grid=True,
                has_profit_lock=False,
            ),
        )

        report = await coordinator.recover_instance("inst-grid")

        # Recovery should complete (grid snapshot is None, but that's OK)
        assert report.connection_ok is True
        assert report.state_ok is True

    @pytest.mark.asyncio
    async def test_recovery_all_instances(self):
        """Recover all registered instances."""
        connection_recovery = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )

        state_recovery = StateRecovery(
            load_instance_fn=lambda iid: {"status": "active"},
        )

        reconciler = RuntimeReconciler()
        persistence = RecoveryPersistence()

        coordinator = RecoveryCoordinator(
            connection_recovery=connection_recovery,
            state_recovery=state_recovery,
            reconciler=reconciler,
            persistence=persistence,
        )

        # Register multiple instances
        for i in range(5):
            coordinator.register_instance(
                f"inst-{i}",
                InstanceContext(
                    instance_id=f"inst-{i}",
                    account_id="acc-1",
                    exchange="binance",
                    symbol="BTCUSDT",
                ),
            )

        # Recover all
        reports = await coordinator.recover_all()

        assert len(reports) == 5
        for _iid, report in reports.items():
            assert report.connection_ok is True
            assert report.state_ok is True
