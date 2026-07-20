"""
Unit tests for PositionAggregator.
"""

from decimal import Decimal

from engine.risk.aggregator import PositionAggregator
from engine.risk.portfolio import PortfolioManager


def _setup_positions() -> PortfolioManager:
    pm = PortfolioManager()
    pm.register_position(
        "inst-1", "acc-1", "binance", "BTCUSDT", "long", Decimal("100"), Decimal("2")
    )
    pm.register_position(
        "inst-2", "acc-1", "binance", "BTCUSDT", "long", Decimal("110"), Decimal("1")
    )
    pm.register_position(
        "inst-3", "acc-2", "bybit", "ETHUSDT", "short", Decimal("50"), Decimal("4")
    )
    return pm


class TestAggregateBySymbol:

    def test_aggregate_btcusdt(self) -> None:
        pm = _setup_positions()
        result = PositionAggregator.aggregate_by_symbol(pm.get_positions())
        btc = result["BTCUSDT"]
        assert btc.total_long_quantity == Decimal("3")
        assert btc.total_short_quantity == Decimal("0")
        assert btc.net_quantity == Decimal("3")
        assert btc.position_count == 2
        # weighted avg = (100*2 + 110*1) / 3 = 310/3
        assert btc.weighted_avg_entry_price == Decimal("310") / Decimal("3")

    def test_aggregate_ethusdt(self) -> None:
        pm = _setup_positions()
        result = PositionAggregator.aggregate_by_symbol(pm.get_positions())
        eth = result["ETHUSDT"]
        assert eth.total_long_quantity == Decimal("0")
        assert eth.total_short_quantity == Decimal("4")
        assert eth.net_quantity == Decimal("-4")
        assert eth.position_count == 1


class TestAggregateByExchange:

    def test_aggregate_binance(self) -> None:
        pm = _setup_positions()
        result = PositionAggregator.aggregate_by_exchange(pm.get_positions())
        binance = result["binance"]
        assert binance.total_long_quantity == Decimal("3")
        assert binance.total_short_quantity == Decimal("0")
        assert binance.position_count == 2

    def test_aggregate_bybit(self) -> None:
        pm = _setup_positions()
        result = PositionAggregator.aggregate_by_exchange(pm.get_positions())
        bybit = result["bybit"]
        assert bybit.total_short_quantity == Decimal("4")
        assert bybit.position_count == 1


class TestAggregateByAccount:

    def test_aggregate_acc1(self) -> None:
        pm = _setup_positions()
        result = PositionAggregator.aggregate_by_account(pm.get_positions())
        acc1 = result["acc-1"]
        assert acc1.total_long_quantity == Decimal("3")
        assert acc1.position_count == 2

    def test_aggregate_acc2(self) -> None:
        pm = _setup_positions()
        result = PositionAggregator.aggregate_by_account(pm.get_positions())
        acc2 = result["acc-2"]
        assert acc2.total_short_quantity == Decimal("4")
        assert acc2.position_count == 1


class TestGetNetPosition:

    def test_net_position(self) -> None:
        pm = _setup_positions()
        net = PositionAggregator.get_net_position(pm.get_positions())
        assert net.total_long_quantity == Decimal("3")
        assert net.total_short_quantity == Decimal("4")
        assert net.net_quantity == Decimal("-1")
        assert net.position_count == 3

    def test_net_position_empty(self) -> None:
        net = PositionAggregator.get_net_position([])
        assert net.net_quantity == Decimal("0")
        assert net.position_count == 0
