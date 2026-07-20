"""
Unit tests for StateRecovery (Layer 2).
"""

from decimal import Decimal

import pytest
from core.domain_types import GridLevel, GridState, PositionEntry
from engine.grid.persistence import GridPersistence
from engine.profit_lock.persistence import ProfitPersistence
from engine.profit_lock.state import ProfitLockState, ProfitLockStatus
from engine.recovery.state import StateRecovery


class TestRecoverTradingProcess:

    @pytest.mark.asyncio
    async def test_recover_process_ok(self) -> None:
        def load_fn(iid: str) -> dict:
            return {"instance_id": iid, "status": "running"}

        sr = StateRecovery(load_instance_fn=load_fn)
        result = await sr.recover_trading_process("inst-1")
        assert result is True
        metrics = sr.get_metrics()
        assert metrics["processes_recovered"] == 1

    @pytest.mark.asyncio
    async def test_recover_process_not_found(self) -> None:
        def load_fn(iid: str) -> dict | None:
            return None

        sr = StateRecovery(load_instance_fn=load_fn)
        result = await sr.recover_trading_process("inst-1")
        assert result is False
        assert sr.get_metrics()["recovery_failures"] == 1

    @pytest.mark.asyncio
    async def test_recover_process_no_fn(self) -> None:
        sr = StateRecovery()
        result = await sr.recover_trading_process("inst-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_recover_process_exception(self) -> None:
        def boom(iid: str) -> dict:
            raise RuntimeError("DB error")

        sr = StateRecovery(load_instance_fn=boom)
        result = await sr.recover_trading_process("inst-1")
        assert result is False


class TestRecoverGrid:

    @pytest.mark.asyncio
    async def test_recover_grid_ok(self) -> None:
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
                ),
            ],
        )
        json_str = GridPersistence.to_json_string(grid_state)
        sr = StateRecovery(load_grid_snapshot_fn=lambda iid: json_str)
        result = await sr.recover_grid("inst-1")
        assert result is not None
        assert result.status == "active"
        assert len(result.levels) == 1
        assert sr.get_metrics()["grids_recovered"] == 1

    @pytest.mark.asyncio
    async def test_recover_grid_no_snapshot(self) -> None:
        sr = StateRecovery(load_grid_snapshot_fn=lambda iid: None)
        result = await sr.recover_grid("inst-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_recover_grid_no_fn(self) -> None:
        sr = StateRecovery()
        result = await sr.recover_grid("inst-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_recover_grid_exception(self) -> None:
        def boom(iid: str) -> str:
            raise RuntimeError("DB error")

        sr = StateRecovery(load_grid_snapshot_fn=boom)
        result = await sr.recover_grid("inst-1")
        assert result is None
        assert sr.get_metrics()["recovery_failures"] == 1


class TestRecoverProfitLock:

    @pytest.mark.asyncio
    async def test_recover_profit_lock_ok(self) -> None:
        state = ProfitLockState(
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
        json_str = ProfitPersistence.to_json_string(state)
        sr = StateRecovery(load_profit_lock_snapshot_fn=lambda iid: json_str)
        result = await sr.recover_profit_lock("inst-1")
        assert result is not None
        assert result.enabled is True
        assert result.status == ProfitLockStatus.MONITORING
        assert sr.get_metrics()["profit_locks_recovered"] == 1

    @pytest.mark.asyncio
    async def test_recover_profit_lock_no_snapshot(self) -> None:
        sr = StateRecovery(load_profit_lock_snapshot_fn=lambda iid: None)
        result = await sr.recover_profit_lock("inst-1")
        assert result is None


class TestRecoverPortfolio:

    @pytest.mark.asyncio
    async def test_recover_portfolio_ok(self) -> None:
        positions = [
            PositionEntry(
                symbol="BTCUSDT",
                side="long",
                quantity=Decimal("2"),
                entry_price=Decimal("100"),
                unrealized_pnl=Decimal("20"),
            ),
        ]
        sr = StateRecovery(fetch_exchange_positions_fn=lambda iid: positions)
        result = await sr.recover_portfolio("inst-1")
        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"
        assert sr.get_metrics()["portfolios_recovered"] == 1

    @pytest.mark.asyncio
    async def test_recover_portfolio_empty(self) -> None:
        sr = StateRecovery(fetch_exchange_positions_fn=lambda iid: [])
        result = await sr.recover_portfolio("inst-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_recover_portfolio_no_fn(self) -> None:
        sr = StateRecovery()
        result = await sr.recover_portfolio("inst-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_recover_portfolio_exception(self) -> None:
        def boom(iid: str) -> list:
            raise RuntimeError("Exchange error")

        sr = StateRecovery(fetch_exchange_positions_fn=boom)
        result = await sr.recover_portfolio("inst-1")
        assert result == []
        assert sr.get_metrics()["recovery_failures"] == 1
