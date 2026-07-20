"""
Unit tests for PortfolioManager.
"""

from decimal import Decimal

import pytest
from core.exceptions import PortfolioError, ValidationError
from engine.risk.portfolio import PortfolioManager


class TestPortfolioManagerRegister:

    def test_register_position(self) -> None:
        pm = PortfolioManager()
        pos = pm.register_position(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="long",
            entry_price=Decimal("100"),
            quantity=Decimal("2"),
        )
        assert pos.instance_id == "inst-1"
        assert pos.side == "long"
        assert pos.entry_price == Decimal("100")
        assert pos.quantity == Decimal("2")
        assert pos.closed is False
        assert pos.realized_pnl == Decimal("0")

    def test_register_duplicate_raises(self) -> None:
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
        with pytest.raises(PortfolioError, match="already exists"):
            pm.register_position(
                "inst-1",
                "acc-1",
                "binance",
                "BTCUSDT",
                "long",
                Decimal("100"),
                Decimal("2"),
            )

    def test_register_invalid_side(self) -> None:
        pm = PortfolioManager()
        with pytest.raises(ValidationError, match="side"):
            pm.register_position(
                "inst-1",
                "acc-1",
                "binance",
                "BTCUSDT",
                "sideways",
                Decimal("100"),
                Decimal("2"),
            )

    def test_register_invalid_price(self) -> None:
        pm = PortfolioManager()
        with pytest.raises(ValidationError, match="entry_price"):
            pm.register_position(
                "inst-1",
                "acc-1",
                "binance",
                "BTCUSDT",
                "long",
                Decimal("0"),
                Decimal("2"),
            )

    def test_register_invalid_quantity(self) -> None:
        pm = PortfolioManager()
        with pytest.raises(ValidationError, match="quantity"):
            pm.register_position(
                "inst-1",
                "acc-1",
                "binance",
                "BTCUSDT",
                "long",
                Decimal("100"),
                Decimal("0"),
            )


class TestPortfolioManagerUpdate:

    def test_update_long_buy_increases_quantity(self) -> None:
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
        pos = pm.update_position("inst-1", Decimal("110"), Decimal("1"), "buy")
        assert pos.quantity == Decimal("3")
        # avg = (100*2 + 110*1) / 3 = 310/3
        assert pos.entry_price == Decimal("310") / Decimal("3")

    def test_update_long_sell_decreases_and_realizes_pnl(self) -> None:
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
        pos = pm.update_position("inst-1", Decimal("120"), Decimal("1"), "sell")
        assert pos.quantity == Decimal("1")
        assert pos.realized_pnl == Decimal("20")  # (120-100)*1
        assert pos.closed is False

    def test_update_long_sell_full_closes_position(self) -> None:
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
        pos = pm.update_position("inst-1", Decimal("120"), Decimal("2"), "sell")
        assert pos.quantity == Decimal("0")
        assert pos.realized_pnl == Decimal("40")
        assert pos.closed is True
        assert pos.closed_at is not None

    def test_update_short_sell_increases_quantity(self) -> None:
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
        pos = pm.update_position("inst-1", Decimal("90"), Decimal("1"), "sell")
        assert pos.quantity == Decimal("3")
        # avg = (100*2 + 90*1) / 3 = 290/3
        assert pos.entry_price == Decimal("290") / Decimal("3")

    def test_update_short_buy_decreases_and_realizes_pnl(self) -> None:
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
        pos = pm.update_position("inst-1", Decimal("90"), Decimal("1"), "buy")
        assert pos.quantity == Decimal("1")
        assert pos.realized_pnl == Decimal("10")  # (100-90)*1

    def test_update_nonexistent_raises(self) -> None:
        pm = PortfolioManager()
        with pytest.raises(PortfolioError, match="not found"):
            pm.update_position("nonexistent", Decimal("100"), Decimal("1"), "buy")

    def test_update_closed_raises(self) -> None:
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
        pm.update_position("inst-1", Decimal("120"), Decimal("2"), "sell")
        # Position is now closed but still in dict (quantity=0)
        # Re-register to test closed scenario
        pm2 = PortfolioManager()
        pm2.register_position(
            "inst-2",
            "acc-1",
            "binance",
            "BTCUSDT",
            "long",
            Decimal("100"),
            Decimal("2"),
        )
        pm2.close_position("inst-2")
        with pytest.raises(PortfolioError, match="not found"):
            pm2.update_position("inst-2", Decimal("120"), Decimal("1"), "sell")

    def test_update_fill_exceeds_quantity_raises(self) -> None:
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
        with pytest.raises(PortfolioError, match="exceeds"):
            pm.update_position("inst-1", Decimal("120"), Decimal("3"), "sell")


class TestPortfolioManagerClose:

    def test_close_position(self) -> None:
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
        pos = pm.close_position("inst-1")
        assert pos.closed is True
        assert pos.closed_at is not None
        assert pm.get_position("inst-1") is None
        assert len(pm.get_closed_positions()) == 1

    def test_close_nonexistent_raises(self) -> None:
        pm = PortfolioManager()
        with pytest.raises(PortfolioError, match="not found"):
            pm.close_position("nonexistent")


class TestPortfolioManagerQuery:

    def test_get_positions_filter_by_exchange(self) -> None:
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
        pm.register_position(
            "inst-2", "acc-1", "bybit", "BTCUSDT", "long", Decimal("100"), Decimal("2")
        )
        result = pm.get_positions(exchange="binance")
        assert len(result) == 1
        assert result[0].instance_id == "inst-1"

    def test_get_positions_filter_by_symbol(self) -> None:
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
        pm.register_position(
            "inst-2", "acc-1", "binance", "ETHUSDT", "long", Decimal("50"), Decimal("4")
        )
        result = pm.get_positions(symbol="ETHUSDT")
        assert len(result) == 1
        assert result[0].symbol == "ETHUSDT"

    def test_get_positions_no_filter_returns_all(self) -> None:
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
        pm.register_position(
            "inst-2", "acc-1", "binance", "ETHUSDT", "long", Decimal("50"), Decimal("4")
        )
        result = pm.get_positions()
        assert len(result) == 2

    def test_get_open_position_count(self) -> None:
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
        pm.register_position(
            "inst-2", "acc-1", "binance", "ETHUSDT", "long", Decimal("50"), Decimal("4")
        )
        assert pm.get_open_position_count() == 2
        pm.close_position("inst-1")
        assert pm.get_open_position_count() == 1

    def test_clear(self) -> None:
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
        pm.clear()
        assert pm.get_open_position_count() == 0
        assert len(pm.get_closed_positions()) == 0
