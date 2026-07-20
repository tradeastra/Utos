"""
Unit tests for RecoveryCoordinator.
"""

from decimal import Decimal

import pytest
from core.exceptions import RecoveryError
from engine.recovery.connection import ConnectionRecovery
from engine.recovery.coordinator import (
    InstanceContext,
    RecoveryCoordinator,
)
from engine.recovery.persistence import RecoveryPersistence
from engine.recovery.reconciler import RuntimeReconciler
from engine.recovery.state import StateRecovery


@pytest.fixture
def coordinator() -> RecoveryCoordinator:
    cr = ConnectionRecovery(
        redis_health_check=lambda: True,
        postgres_health_check=lambda: True,
    )
    sr = StateRecovery(
        load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
    )
    rc = RuntimeReconciler()
    persistence = RecoveryPersistence()
    return RecoveryCoordinator(
        connection_recovery=cr,
        state_recovery=sr,
        reconciler=rc,
        persistence=persistence,
    )


class TestRegisterInstance:

    def test_register(self, coordinator: RecoveryCoordinator) -> None:
        ctx = InstanceContext(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            has_grid=True,
            has_profit_lock=True,
        )
        coordinator.register_instance("inst-1", ctx)
        assert "inst-1" in coordinator.get_registered_instances()
        status = coordinator.get_recovery_status("inst-1")
        assert status.state == "idle"
        assert coordinator.get_metrics()["instances_registered"] == 1


class TestRecoverInstance:

    @pytest.mark.asyncio
    async def test_recover_success(self, coordinator: RecoveryCoordinator) -> None:
        ctx = InstanceContext(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            has_grid=False,
            has_profit_lock=False,
        )
        coordinator.register_instance("inst-1", ctx)
        report = await coordinator.recover_instance("inst-1")
        assert report.instance_id == "inst-1"
        assert report.connection_ok is True
        assert report.state_ok is True
        assert report.completed_at is not None
        assert len(report.errors) == 0
        status = coordinator.get_recovery_status("inst-1")
        assert status.state == "completed"
        assert coordinator.get_metrics()["recoveries_completed"] == 1

    @pytest.mark.asyncio
    async def test_recover_unregistered_raises(
        self, coordinator: RecoveryCoordinator
    ) -> None:
        with pytest.raises(RecoveryError, match="not registered"):
            await coordinator.recover_instance("nonexistent")

    @pytest.mark.asyncio
    async def test_recover_with_connection_failure(self) -> None:
        cr = ConnectionRecovery(
            redis_health_check=lambda: False,
            postgres_health_check=lambda: True,
        )
        sr = StateRecovery()
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)
        coord.register_instance(
            "inst-1",
            InstanceContext(
                instance_id="inst-1",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
            ),
        )
        report = await coord.recover_instance("inst-1")
        assert report.connection_ok is False
        assert any("Connection recovery" in e for e in report.errors)

    @pytest.mark.asyncio
    async def test_recover_with_grid_and_profit_lock(self) -> None:
        from core.domain_types import GridLevel, GridState
        from engine.grid.persistence import GridPersistence
        from engine.profit_lock.persistence import ProfitPersistence
        from engine.profit_lock.state import ProfitLockState, ProfitLockStatus

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
                )
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

        cr = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )
        sr = StateRecovery(
            load_instance_fn=lambda iid: {"instance_id": iid, "status": "running"},
            load_grid_snapshot_fn=lambda iid: grid_json,
            load_profit_lock_snapshot_fn=lambda iid: pl_json,
        )
        rc = RuntimeReconciler()
        coord = RecoveryCoordinator(cr, sr, rc)
        coord.register_instance(
            "inst-1",
            InstanceContext(
                instance_id="inst-1",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
                has_grid=True,
                has_profit_lock=True,
            ),
        )
        report = await coord.recover_instance("inst-1")
        assert report.connection_ok is True
        assert report.state_ok is True


class TestRecoverAll:

    @pytest.mark.asyncio
    async def test_recover_all(self, coordinator: RecoveryCoordinator) -> None:
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
        results = await coordinator.recover_all()
        assert len(results) == 5
        for _iid, report in results.items():
            assert report.connection_ok is True
            assert report.state_ok is True


class TestRecoveryStatus:

    def test_status_idle_before_recovery(
        self, coordinator: RecoveryCoordinator
    ) -> None:
        coordinator.register_instance(
            "inst-1",
            InstanceContext(
                instance_id="inst-1",
                account_id="acc-1",
                exchange="binance",
                symbol="BTCUSDT",
            ),
        )
        status = coordinator.get_recovery_status("inst-1")
        assert status.state == "idle"
        assert status.started_at is None

    def test_status_nonexistent(self, coordinator: RecoveryCoordinator) -> None:
        status = coordinator.get_recovery_status("nonexistent")
        assert status.state == "idle"
