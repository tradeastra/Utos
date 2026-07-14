"""
Unit tests for RiskManager.
"""

from decimal import Decimal

import pytest

from core.types import RiskLevel
from engine.risk.exposure import ExposureManager
from engine.risk.manager import RiskLimits, RiskManager
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


class TestRiskManagerParameters:

    def test_set_and_get_parameters(self, risk_manager: RiskManager) -> None:
        limits = risk_manager.get_risk_parameters("user-1")
        assert limits.max_exposure_per_symbol == Decimal("10000")
        assert limits.max_open_positions == 5

    def test_default_parameters(self, portfolio: PortfolioManager, exposure: ExposureManager) -> None:
        rm = RiskManager(portfolio=portfolio, exposure=exposure)
        limits = rm.get_risk_parameters("nonexistent")
        assert limits.max_exposure_per_symbol == Decimal("100000")


class TestCheckOrderRiskAllowed:

    def test_order_within_limits_allowed(
        self, risk_manager: RiskManager, portfolio: PortfolioManager
    ) -> None:
        result = risk_manager.check_order_risk(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("1"),
            price=Decimal("100"),
            user_id="user-1",
        )
        assert result.allowed is True
        assert result.reason is None

    def test_order_allowed_metrics_tracked(
        self, risk_manager: RiskManager
    ) -> None:
        risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("1"), Decimal("100"), "user-1",
        )
        metrics = risk_manager.get_metrics("user-1")
        assert metrics["orders_checked"] == 1
        assert metrics["orders_allowed"] == 1
        assert metrics["orders_denied"] == 0


class TestCheckOrderRiskDenied:

    def test_order_exceeds_max_position_size(
        self, risk_manager: RiskManager
    ) -> None:
        result = risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("100"), Decimal("100"), "user-1",
        )
        assert result.allowed is False
        assert "max_position_size" in result.reason

    def test_order_exceeds_max_exposure_per_symbol(
        self, risk_manager: RiskManager, portfolio: PortfolioManager
    ) -> None:
        # Register existing position to add to exposure
        portfolio.register_position(
            "inst-existing", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("50"),
        )
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("100"))
        # Existing exposure: 100*50 = 5000, new order: 40*100 = 4000, total = 9000 < 10000 (symbol ok)
        # but 4000 < 5000 (position size ok) so this should pass.
        # Use qty=50: 50*100 = 5000, total = 10000 = limit, still ok.
        # Use qty=51: 51*100 = 5100 > 5000 max_position_size → denied by position size first.
        # So we need a smaller price to avoid hitting position size.
        # Use price=50: existing=100*50=5000, new=50*100=5000 > 5000 position size.
        # Better: increase max_position_size for this test.
        risk_manager.set_risk_parameters("user-1", RiskLimits(
            max_exposure_per_symbol=Decimal("10000"),
            max_exposure_per_exchange=Decimal("50000"),
            max_open_positions=5,
            max_position_size=Decimal("20000"),
            max_capital_per_instance=Decimal("20000"),
        ))
        # Existing exposure: 100*50 = 5000, new order: 100*60 = 6000, total = 11000 > 10000
        result = risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("60"), Decimal("100"), "user-1",
        )
        assert result.allowed is False
        assert "max_exposure_per_symbol" in result.reason

    def test_order_exceeds_max_open_positions(
        self, risk_manager: RiskManager, portfolio: PortfolioManager
    ) -> None:
        # Register 5 positions (max_open_positions=5)
        for i in range(5):
            portfolio.register_position(
                f"inst-{i}", "acc-1", "binance", "BTCUSDT", "long",
                Decimal("100"), Decimal("1"),
            )
        result = risk_manager.check_order_risk(
            "inst-new", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("1"), Decimal("100"), "user-1",
        )
        assert result.allowed is False
        assert "max_open_positions" in result.reason

    def test_order_exceeds_max_exposure_per_exchange(
        self, risk_manager: RiskManager, portfolio: PortfolioManager
    ) -> None:
        # Set up position with large exposure on binance
        portfolio.register_position(
            "inst-existing", "acc-1", "binance", "ETHUSDT", "long",
            Decimal("50"), Decimal("900"),
        )
        risk_manager.on_price_update("user-1", "ETHUSDT", Decimal("50"))
        # ETH exposure: 50*900 = 45000, new BTC order: 100*60 = 6000 > 5000 max_position_size
        # Need to increase max_position_size to test exchange limit
        risk_manager.set_risk_parameters("user-1", RiskLimits(
            max_exposure_per_symbol=Decimal("100000"),
            max_exposure_per_exchange=Decimal("50000"),
            max_open_positions=5,
            max_position_size=Decimal("20000"),
            max_capital_per_instance=Decimal("20000"),
        ))
        # ETH exposure: 50*900 = 45000, new BTC order: 100*60 = 6000, total = 51000 > 50000
        result = risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("60"), Decimal("100"), "user-1",
        )
        assert result.allowed is False
        assert "max_exposure_per_exchange" in result.reason

    def test_denied_metrics_tracked(self, risk_manager: RiskManager) -> None:
        risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("100"), Decimal("100"), "user-1",
        )
        metrics = risk_manager.get_metrics("user-1")
        assert metrics["orders_denied"] == 1


class TestCheckPortfolioRisk:

    def test_low_risk(self, risk_manager: RiskManager, portfolio: PortfolioManager) -> None:
        portfolio.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("1"),
        )
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("100"))
        assessment = risk_manager.check_portfolio_risk("user-1")
        assert assessment.risk_level == RiskLevel.LOW

    def test_high_risk(self, risk_manager: RiskManager, portfolio: PortfolioManager) -> None:
        portfolio.register_position(
            "inst-1", "acc-1", "binance", "BTCUSDT", "long",
            Decimal("100"), Decimal("600"),
        )
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("100"))
        # total exposure = 60000 > 50000 (max_exposure_per_exchange)
        assessment = risk_manager.check_portfolio_risk("user-1")
        assert assessment.risk_level == RiskLevel.HIGH


class TestPriceUpdate:

    def test_price_update_tracked(self, risk_manager: RiskManager) -> None:
        risk_manager.on_price_update("user-1", "BTCUSDT", Decimal("110"))
        metrics = risk_manager.get_metrics("user-1")
        assert metrics["price_updates"] == 1


class TestInstanceCapital:

    def test_set_and_get_instance_capital(self, risk_manager: RiskManager) -> None:
        risk_manager.set_instance_capital("inst-1", Decimal("15000"))
        assert risk_manager.get_instance_capital("inst-1") == Decimal("15000")

    def test_order_denied_when_capital_exceeds(
        self, risk_manager: RiskManager
    ) -> None:
        risk_manager.set_instance_capital("inst-1", Decimal("25000"))
        result = risk_manager.check_order_risk(
            "inst-1", "acc-1", "binance", "BTCUSDT", "buy",
            Decimal("1"), Decimal("100"), "user-1",
        )
        assert result.allowed is False
        assert "max_capital_per_instance" in result.reason
