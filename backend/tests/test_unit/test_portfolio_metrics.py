"""
Unit tests for PortfolioMetrics.
"""

from decimal import Decimal

from engine.risk.metrics import PortfolioMetrics
from engine.risk.portfolio import PortfolioManager


class TestUnrealizedPnl:

    def test_long_profit(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pnl = PortfolioMetrics.calculate_unrealized_pnl(
            pm.get_positions(), {"BTCUSDT": Decimal("110")}
        )
        assert pnl == Decimal("20")

    def test_long_loss(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pnl = PortfolioMetrics.calculate_unrealized_pnl(
            pm.get_positions(), {"BTCUSDT": Decimal("90")}
        )
        assert pnl == Decimal("-20")

    def test_short_profit(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "short", Decimal("100"), Decimal("2"))
        pnl = PortfolioMetrics.calculate_unrealized_pnl(
            pm.get_positions(), {"BTCUSDT": Decimal("90")}
        )
        assert pnl == Decimal("20")

    def test_missing_price_skipped(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pnl = PortfolioMetrics.calculate_unrealized_pnl(pm.get_positions(), {})
        assert pnl == Decimal("0")

    def test_multiple_positions(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pm.register_position("inst-2", "acc-1", "binance", "ETHUSDT", "long", Decimal("50"), Decimal("4"))
        pnl = PortfolioMetrics.calculate_unrealized_pnl(
            pm.get_positions(), {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        )
        # BTC: (110-100)*2 = 20, ETH: (55-50)*4 = 20, total = 40
        assert pnl == Decimal("40")


class TestRealizedPnl:

    def test_realized_pnl(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pm.update_position("inst-1", Decimal("120"), Decimal("1"), "sell")
        pm.close_position("inst-1")
        pnl = PortfolioMetrics.calculate_realized_pnl(pm.get_closed_positions())
        assert pnl == Decimal("20")

    def test_realized_pnl_empty(self) -> None:
        pnl = PortfolioMetrics.calculate_realized_pnl([])
        assert pnl == Decimal("0")


class TestTotalExposure:

    def test_total_exposure(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pm.register_position("inst-2", "acc-1", "binance", "ETHUSDT", "short", Decimal("50"), Decimal("4"))
        exposure = PortfolioMetrics.calculate_total_exposure(
            pm.get_positions(), {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        )
        # 110*2 + 55*4 = 220 + 220 = 440
        assert exposure == Decimal("440")


class TestDrawdown:

    def test_no_drawdown(self) -> None:
        history = [Decimal("100"), Decimal("110"), Decimal("120")]
        dd = PortfolioMetrics.calculate_drawdown(history)
        assert dd == Decimal("0")

    def test_drawdown(self) -> None:
        history = [Decimal("100"), Decimal("120"), Decimal("80"), Decimal("90")]
        dd = PortfolioMetrics.calculate_drawdown(history)
        # peak=120, trough=80, dd=40
        assert dd == Decimal("40")

    def test_drawdown_empty(self) -> None:
        dd = PortfolioMetrics.calculate_drawdown([])
        assert dd == Decimal("0")

    def test_drawdown_all_declining(self) -> None:
        history = [Decimal("100"), Decimal("80"), Decimal("60")]
        dd = PortfolioMetrics.calculate_drawdown(history)
        assert dd == Decimal("40")


class TestMarginUsage:

    def test_margin_usage(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        usage = PortfolioMetrics.calculate_margin_usage(
            pm.get_positions(), {"BTCUSDT": Decimal("110")}, Decimal("1000")
        )
        # exposure = 110*2 = 220, margin = 220/1000 * 100 = 22%
        assert usage == Decimal("22")

    def test_margin_usage_zero_balance(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        usage = PortfolioMetrics.calculate_margin_usage(
            pm.get_positions(), {"BTCUSDT": Decimal("110")}, Decimal("0")
        )
        assert usage == Decimal("0")


class TestGenerateReport:

    def test_full_report(self) -> None:
        pm = PortfolioManager()
        pm.register_position("inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2"))
        pm.update_position("inst-1", Decimal("120"), Decimal("1"), "sell")
        pm.close_position("inst-1")

        pm.register_position("inst-2", "acc-1", "binance", "ETHUSDT", "long", Decimal("50"), Decimal("4"))

        report = PortfolioMetrics.generate_report(
            positions=pm.get_positions(),
            current_prices={"ETHUSDT": Decimal("55")},
            closed_positions=pm.get_closed_positions(),
            pnl_history=[Decimal("0"), Decimal("20"), Decimal("10")],
            account_balance=Decimal("1000"),
        )
        assert report.unrealized_pnl == Decimal("20")  # (55-50)*4
        assert report.realized_pnl == Decimal("20")  # from closed BTC position
        assert report.total_pnl == Decimal("40")
        assert report.total_exposure == Decimal("220")  # 55*4
        assert report.drawdown == Decimal("10")  # peak=20, trough=10
        assert report.margin_usage == Decimal("22")  # 220/1000*100
        assert report.position_count == 1
        assert report.timestamp is not None
