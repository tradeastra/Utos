"""
Unit tests for ProfitCalculator.
"""

from decimal import Decimal

import pytest

from core.exceptions import ValidationError
from engine.profit_lock.calculator import ProfitCalculator


class TestProfitCalculatorValidation:

    def test_entry_price_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="entry_price must be > 0"):
            ProfitCalculator.calculate(Decimal("0"), Decimal("100"), Decimal("1"), "long")

    def test_current_price_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="current_price must be > 0"):
            ProfitCalculator.calculate(Decimal("100"), Decimal("0"), Decimal("1"), "long")

    def test_quantity_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="quantity must be > 0"):
            ProfitCalculator.calculate(Decimal("100"), Decimal("100"), Decimal("0"), "long")

    def test_side_must_be_long_or_short(self) -> None:
        with pytest.raises(ValidationError, match="side must be"):
            ProfitCalculator.calculate(Decimal("100"), Decimal("110"), Decimal("1"), "sideways")


class TestProfitCalculatorLong:

    def test_profitable_long(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("110"),
            quantity=Decimal("2"),
            side="long",
        )
        assert result.floating_profit == Decimal("20")
        assert result.is_profitable is True

    def test_losing_long(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("90"),
            quantity=Decimal("2"),
            side="long",
        )
        assert result.floating_profit == Decimal("-20")
        assert result.is_profitable is False

    def test_breakeven_long(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("100"),
            quantity=Decimal("2"),
            side="long",
        )
        assert result.floating_profit == Decimal("0")
        assert result.is_profitable is False


class TestProfitCalculatorShort:

    def test_profitable_short(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("90"),
            quantity=Decimal("2"),
            side="short",
        )
        assert result.floating_profit == Decimal("20")
        assert result.is_profitable is True

    def test_losing_short(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("110"),
            quantity=Decimal("2"),
            side="short",
        )
        assert result.floating_profit == Decimal("-20")
        assert result.is_profitable is False


class TestProfitPercentage:

    def test_profit_percentage_long(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("110"),
            quantity=Decimal("2"),
            side="long",
        )
        # profit = 20, investment = 200, percentage = 10%
        assert result.profit_percentage == Decimal("10")

    def test_profit_percentage_short(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("95"),
            quantity=Decimal("1"),
            side="short",
        )
        # profit = 5, investment = 100, percentage = 5%
        assert result.profit_percentage == Decimal("5")

    def test_negative_profit_percentage(self) -> None:
        result = ProfitCalculator.calculate(
            entry_price=Decimal("100"),
            current_price=Decimal("80"),
            quantity=Decimal("1"),
            side="long",
        )
        assert result.profit_percentage == Decimal("-20")
