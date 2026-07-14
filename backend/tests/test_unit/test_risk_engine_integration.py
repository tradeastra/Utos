"""
Integration tests for Portfolio & Risk Engine.

Tests the full flow: positions → exposure → risk check → portfolio assessment.
Also verifies independence from Grid Engine and Profit Lock Engine.
"""

import inspect

from decimal import Decimal

import pytest

from core.types import RiskLevel
from engine.risk.aggregator import PositionAggregator
from engine.risk.exposure import ExposureManager
from engine.risk.manager import RiskLimits, RiskManager
from engine.risk.metrics import PortfolioMetrics
from engine.risk.portfolio import PortfolioManager


@pytest.fixture
def portfolio() -> PortfolioManager:
    return PortfolioManager()


@pytest.fixture
def exposure() -> ExposureManager:
    return ExposureManager()


@pytest.fixture
def risk_manager(portfolio: PortfolioManager, exposure: ExposureManager) -> RiskManager:
    rm = RiskManager(portfolio=portfolio, exposure=exposure)
    rm.set_risk_parameters("user-1", RiskLimits(
        max_exposure_per_symbol=Decimal("10000"),
        max_exposure_per_exchange=Decimal("50000"),
        max_open_positions=5,
        max_position_size=Decimal("5000"),
        max_capital_per_instance=Decimal("20000"),
    ))
    return rm


class TestFullRiskFlow:

    def test_order_allowed_then_position_registered_then_denied(
        self,
        risk_manager: RiskManager,
        portfolio: PortfolioManager,
    ) -> None:
        """1. Check order risk → allowed → register position → check again → denied (exposure)."""
        # 1. First order: 2 BTC @ 100 = 200 notional, well within limits
        result = risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("2"), Decimal("100"), "user-1",
        )
        assert result.allowed is True

        # 2. Register the position
        portfolio.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("2"),
        )
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("100"))

        # 3. Try to add 60 BTC @ 100 = 6000 notional > 5000 max_position_size
        #    Need to increase max_position_size to test exposure limit
        risk_manager.set_risk_parameters("user-1", RiskLimits(
            max_exposure_per_symbol=Decimal("10000"),
            max_exposure_per_exchange=Decimal("50000"),
            max_open_positions=5,
            max_position_size=Decimal("20000"),
            max_capital_per_instance=Decimal("20000"),
        ))
        # Existing: 100*2 = 200, new: 100*100 = 10000, total = 10200 > 10000
        result = risk_manager.check_order_risk(
            "inst-2", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("100"), Decimal("100"), "user-1",
        )
        assert result.allowed is False
        assert "max_exposure_per_symbol" in result.reason

    def test_multiple_positions_portfolio_assessment(
        self,
        risk_manager: RiskManager,
        portfolio: PortfolioManager,
    ) -> None:
        """Register multiple positions and assess portfolio risk."""
        portfolio.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("2"),
        )
        portfolio.register_position(
            "inst-2", "acc-1", "binance", "ETHUSDT", "long",
            Decimal("50"), Decimal("10"),
        )
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("110"))
        risk_manager.on_price_update("user-1", "ETHUSDT", Decimal("55"))

        assessment = risk_manager.check_portfolio_risk("user-1")
        # total exposure = 110*2 + 55*10 = 220 + 550 = 770 < 50000
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.total_exposure == Decimal("770")

    def test_full_portfolio_report(
        self,
        portfolio: PortfolioManager,
    ) -> None:
        """Generate a full portfolio report with PnL, exposure, drawdown."""
        # Open position
        portfolio.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("2"),
        )
        # Partial close with profit
        portfolio.update_position("inst-1", Decimal("120"), Decimal("1"), "sell")
        portfolio.close_position("inst-1")

        # Open new position
        portfolio.register_position(
            "inst-2", "acc-1", "binance", "ETHUSDT", "long",
            Decimal("50"), Decimal("4"),
        )

        report = PortfolioMetrics.generate_report(
            positions=portfolio.get_positions(),
            current_prices={"ETHUSDT": Decimal("55")},
            closed_positions=portfolio.get_closed_positions(),
            pnl_history=[Decimal("0"), Decimal("20"), Decimal("15")],
            account_balance=Decimal("1000"),
        )
        assert report.unrealized_pnl == Decimal("20")  # (55-50)*4
        assert report.realized_pnl == Decimal("20")
        assert report.total_pnl == Decimal("40")
        assert report.drawdown == Decimal("5")  # peak=20, trough=15
        assert report.position_count == 1

    def test_aggregator_with_risk_manager(
        self,
        risk_manager: RiskManager,
        portfolio: PortfolioManager,
    ) -> None:
        """Verify aggregator works with positions tracked by portfolio manager."""
        portfolio.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("2"),
        )
        portfolio.register_position(
            "inst-2", "acc-2", "bybit", "BTCUSDT", "short",
            Decimal("110"), Decimal("1"),
        )

        by_symbol = PositionAggregator.aggregate_by_symbol(portfolio.get_positions())
        btc = by_symbol["BTCUSDT"]
        assert btc.total_long_quantity == Decimal("2")
        assert btc.total_short_quantity == Decimal("1")
        assert btc.net_quantity == Decimal("1")
        assert btc.position_count == 2


class TestRiskEngineIndependence:

    def test_no_grid_engine_imports(self) -> None:
        """Verify risk engine does NOT import from grid engine."""
        import engine.risk.manager as rm_module
        source = inspect.getsource(rm_module)
        import_lines = [
            line.strip() for line in source.split("\n")
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "engine.grid" not in line, f"Risk manager imports from grid: {line}"
            assert "GridEngine" not in line, f"Risk manager imports GridEngine: {line}"

    def test_no_profit_lock_imports(self) -> None:
        """Verify risk engine does NOT import from profit lock engine."""
        import engine.risk.manager as rm_module
        source = inspect.getsource(rm_module)
        import_lines = [
            line.strip() for line in source.split("\n")
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "engine.profit_lock" not in line, f"Risk manager imports from profit_lock: {line}"
            assert "ProfitLockEngine" not in line, f"Risk manager imports ProfitLockEngine: {line}"

    def test_no_execution_engine_imports(self) -> None:
        """Verify risk manager does NOT import from execution engine (it's a gatekeeper, not executor)."""
        import engine.risk.manager as rm_module
        source = inspect.getsource(rm_module)
        import_lines = [
            line.strip() for line in source.split("\n")
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "engine.execution" not in line, f"Risk manager imports from execution: {line}"
            assert "ExecutionEngine" not in line, f"Risk manager imports ExecutionEngine: {line}"


class TestRiskManagerMetricsTracking:

    def test_metrics_after_multiple_checks(
        self,
        risk_manager: RiskManager,
        portfolio: PortfolioManager,
    ) -> None:
        """Verify metrics are tracked across multiple order checks."""
        # Allowed order
        risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("1"), Decimal("100"), "user-1",
        )
        # Denied order (too large)
        risk_manager.check_order_risk(
            "inst-2", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("100"), Decimal("100"), "user-1",
        )
        # Price updates
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("110"))
        risk_manager.on_price_update("user-1", "ETHUSDT", Decimal("55"))

        metrics = risk_manager.get_metrics("user-1")
        assert metrics["orders_checked"] == 2
        assert metrics["orders_allowed"] == 1
        assert metrics["orders_denied"] == 1
        assert metrics["price_updates"] == 2
