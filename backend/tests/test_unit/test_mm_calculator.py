"""
Unit tests for MMCalculator — per-coin DCA allocation model.

Formula under test:
  buy_amount = capital / (steps * coin_group.max_coins)
  max_coins  = coin_group.max_coins
  steps      = preset steps (MM30=30, MM50=50, MM70=70, custom=user-defined)
  min_volume = buy_amount * 10
  buy_amount must be >= MIN_BUY_AMOUNT ($15)
"""

from decimal import Decimal

import pytest
from core.exceptions import ValidationError
from services.mm_calculator import (
    BUILTIN_PRESETS,
    MIN_BUY_AMOUNT,
    MMCalculator,
)


class TestMMCalculatorBasic:
    def setup_method(self) -> None:
        self.calc = MMCalculator()

    def test_mm50_top10_correct_allocation(self) -> None:
        # $7,500 / (50 steps * 10 coins) = $15.00 per layer
        result = self.calc.calculate(
            preset_type="mm50",
            capital=Decimal("7500"),
            coin_group_name="Top 10",
            coin_group_max_coins=10,
        )
        assert result.buy_amount == Decimal("15.00")
        assert result.max_coins == 10
        assert result.steps == 50
        assert result.min_volume_filter == Decimal("150.0")

    def test_mm30_top3_correct_allocation(self) -> None:
        # $1,350 / (30 * 3) = $15.00
        result = self.calc.calculate(
            preset_type="mm30",
            capital=Decimal("1350"),
            coin_group_name="Top 3",
            coin_group_max_coins=3,
        )
        assert result.buy_amount == Decimal("15.00")
        assert result.max_coins == 3
        assert result.steps == 30

    def test_mm70_all_correct_allocation(self) -> None:
        # All = 999 coins; need huge capital: 70 * 999 * 15 = $1,048,950
        capital = Decimal("1048950")
        result = self.calc.calculate(
            preset_type="mm70",
            capital=capital,
            coin_group_name="All",
            coin_group_max_coins=999,
        )
        assert result.buy_amount == Decimal("15.00")
        assert result.max_coins == 999
        assert result.steps == 70

    def test_buy_amount_quantized_down_to_cents(self) -> None:
        # $1000 / (50 * 10) = $2.00 — but below $15 min, so use $7500 + $1
        # $7501 / 500 = $15.002 -> quantized down to $15.00
        result = self.calc.calculate(
            preset_type="mm50",
            capital=Decimal("7501"),
            coin_group_name="Top 10",
            coin_group_max_coins=10,
        )
        assert result.buy_amount == Decimal("15.00")


class TestMMCalculatorValidation:
    def setup_method(self) -> None:
        self.calc = MMCalculator()

    def test_requires_coin_group_max_coins(self) -> None:
        with pytest.raises(ValidationError, match="coin_group_max_coins is required"):
            self.calc.calculate(
                preset_type="mm50",
                capital=Decimal("5000"),
                coin_group_name="Top 10",
                coin_group_max_coins=None,
            )

    def test_zero_coin_group_max_coins_rejected(self) -> None:
        with pytest.raises(ValidationError, match="coin_group_max_coins is required"):
            self.calc.calculate(
                preset_type="mm50",
                capital=Decimal("5000"),
                coin_group_name="Top 10",
                coin_group_max_coins=0,
            )

    def test_invalid_preset_type_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid preset type"):
            self.calc.calculate(
                preset_type="mm99",
                capital=Decimal("5000"),
                coin_group_name="Top 10",
                coin_group_max_coins=10,
            )

    def test_capital_below_preset_minimum_rejected(self) -> None:
        # MM50 min capital = $500
        with pytest.raises(ValidationError, match="below minimum"):
            self.calc.calculate(
                preset_type="mm50",
                capital=Decimal("400"),
                coin_group_name="Top 10",
                coin_group_max_coins=10,
            )

    def test_mm30_incompatible_coin_group_rejected(self) -> None:
        # MM30 only allowed for Top 3 / Top 5
        with pytest.raises(ValidationError, match="only compatible"):
            self.calc.calculate(
                preset_type="mm30",
                capital=Decimal("10000"),
                coin_group_name="Top 20",
                coin_group_max_coins=20,
            )

    def test_buy_amount_below_15_rejected(self) -> None:
        # $1200 / (50 * 10) = $2.40 — below $15 min
        with pytest.raises(ValidationError, match="below minimum"):
            self.calc.calculate(
                preset_type="mm50",
                capital=Decimal("1200"),
                coin_group_name="Top 10",
                coin_group_max_coins=10,
            )

    def test_buy_amount_below_15_error_mentions_required_capital(self) -> None:
        # $1200 / (50 * 10) = $2.40; required = 50 * 10 * 15 = $7500
        with pytest.raises(ValidationError, match=r"7500"):
            self.calc.calculate(
                preset_type="mm50",
                capital=Decimal("1200"),
                coin_group_name="Top 10",
                coin_group_max_coins=10,
            )


class TestMMCalculatorCustom:
    def setup_method(self) -> None:
        self.calc = MMCalculator()

    def test_custom_preset_uses_custom_steps(self) -> None:
        # 10 steps * 3 coins * $15 = $450
        result = self.calc.calculate(
            preset_type="custom",
            capital=Decimal("450"),
            coin_group_name="Top 3",
            coin_group_max_coins=3,
            custom_steps=10,
        )
        assert result.buy_amount == Decimal("15.00")
        assert result.steps == 10
        assert result.max_coins == 3

    def test_custom_preset_requires_custom_steps(self) -> None:
        with pytest.raises(ValidationError, match="custom_steps"):
            self.calc.calculate(
                preset_type="custom",
                capital=Decimal("450"),
                coin_group_name="Top 3",
                coin_group_max_coins=3,
            )

    def test_custom_preset_steps_cannot_exceed_200(self) -> None:
        with pytest.raises(ValidationError, match="cannot exceed 200"):
            self.calc.calculate(
                preset_type="custom",
                capital=Decimal("1000000"),
                coin_group_name="Top 3",
                coin_group_max_coins=3,
                custom_steps=201,
            )


class TestBuiltinPresets:
    def test_mm30_allowed_groups_include_top3_and_top5(self) -> None:
        assert BUILTIN_PRESETS["mm30"]["allowed_coin_groups"] == ["Top 3", "Top 5"]

    def test_mm50_allowed_groups(self) -> None:
        assert BUILTIN_PRESETS["mm50"]["allowed_coin_groups"] == ["Top 10", "Top 20"]

    def test_mm70_allowed_groups(self) -> None:
        assert BUILTIN_PRESETS["mm70"]["allowed_coin_groups"] == ["Top 20", "Top 50", "All"]

    def test_min_buy_amount_is_15(self) -> None:
        assert MIN_BUY_AMOUNT == Decimal("15")
