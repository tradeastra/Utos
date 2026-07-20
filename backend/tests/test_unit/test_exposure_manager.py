"""
Unit tests for ExposureManager.
"""

from decimal import Decimal

from engine.risk.exposure import ExposureManager
from engine.risk.portfolio import PortfolioManager


def _setup_positions() -> PortfolioManager:
    pm = PortfolioManager()
    pm.register_position(
        "inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2")
    )
    pm.register_position(
        "inst-2", "acc-1", "binance", "ETHUSDT", "long", Decimal("50"), Decimal("4")
    )
    pm.register_position(
        "inst-3", "acc-2", "bybit", "BTCUSDT", "short", Decimal("100"), Decimal("1")
    )
    return pm


class TestExposureByExchange:

    def test_by_exchange(self) -> None:
        pm = _setup_positions()
        prices = {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        result = ExposureManager.get_exposure_by_exchange(pm.get_positions(), prices)
        # binance: 110*2 + 55*4 = 220 + 220 = 440
        assert result["binance"] == Decimal("440")
        # bybit: 110*1 = 110
        assert result["bybit"] == Decimal("110")


class TestExposureByAccount:

    def test_by_account(self) -> None:
        pm = _setup_positions()
        prices = {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        result = ExposureManager.get_exposure_by_account(pm.get_positions(), prices)
        # acc-1: 110*2 + 55*4 = 440
        assert result["acc-1"] == Decimal("440")
        # acc-2: 110*1 = 110
        assert result["acc-2"] == Decimal("110")


class TestExposureBySymbol:

    def test_by_symbol(self) -> None:
        pm = _setup_positions()
        prices = {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        result = ExposureManager.get_exposure_by_symbol(pm.get_positions(), prices)
        # BTCUSDT: 110*2 + 110*1 = 330
        assert result["BTCUSDT"] == Decimal("330")
        # ETHUSDT: 55*4 = 220
        assert result["ETHUSDT"] == Decimal("220")


class TestNetExposure:

    def test_net_exposure(self) -> None:
        pm = _setup_positions()
        prices = {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        net = ExposureManager.get_net_exposure(pm.get_positions(), prices)
        # long: 110*2 + 55*4 = 440, short: 110*1 = 110
        # net = 440 - 110 = 330
        assert net == Decimal("330")

    def test_net_exposure_all_long(self) -> None:
        pm = PortfolioManager()
        pm.register_position(
            "inst-1",
            "acc-1",
            "binance",
            "BTCUSDT",
            "long",
            Decimal("100"),
            Decimal("2"),
        )
        prices = {"BTCUSDT": Decimal("110")}
        net = ExposureManager.get_net_exposure(pm.get_positions(), prices)
        assert net == Decimal("220")

    def test_net_exposure_all_short(self) -> None:
        pm = PortfolioManager()
        pm.register_position(
            "inst-1",
            "acc-1",
            "binance",
            "BTCUSDT",
            "short",
            Decimal("100"),
            Decimal("2"),
        )
        prices = {"BTCUSDT": Decimal("110")}
        net = ExposureManager.get_net_exposure(pm.get_positions(), prices)
        assert net == Decimal("-220")


class TestCalculateExposure:

    def test_full_report(self) -> None:
        pm = _setup_positions()
        prices = {"BTCUSDT": Decimal("110"), "ETHUSDT": Decimal("55")}
        report = ExposureManager.calculate_exposure(pm.get_positions(), prices)
        assert report.long_exposure == Decimal("440")
        assert report.short_exposure == Decimal("110")
        assert report.total_exposure == Decimal("550")
        assert report.net_exposure == Decimal("330")
        assert report.by_exchange["binance"] == Decimal("440")
        assert report.by_account["acc-1"] == Decimal("440")
        assert report.by_symbol["BTCUSDT"] == Decimal("330")

    def test_empty_positions(self) -> None:
        report = ExposureManager.calculate_exposure([], {})
        assert report.total_exposure == Decimal("0")
        assert report.long_exposure == Decimal("0")
        assert report.short_exposure == Decimal("0")
        assert report.net_exposure == Decimal("0")

    def test_fallback_to_entry_price(self) -> None:
        pm = PortfolioManager()
        pm.register_position(
            "inst-1",
            "acc-1",
            "binance",
            "BTCUSDT",
            "long",
            Decimal("100"),
            Decimal("2"),
        )
        # No price in dict → falls back to entry_price
        report = ExposureManager.calculate_exposure(pm.get_positions(), {})
        assert report.total_exposure == Decimal("200")  # 100*2
