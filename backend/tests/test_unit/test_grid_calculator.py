"""
Unit tests for GridCalculator.
"""

from decimal import Decimal

import pytest
from core.domain_types import GridLevelStatus
from core.exceptions import ValidationError
from engine.grid.calculator import GridCalculator


class TestGridCalculatorValidation:

    def test_upper_must_be_greater_than_lower(self) -> None:
        with pytest.raises(ValidationError, match="upper_price.*must be > lower_price"):
            GridCalculator.calculate_levels(
                upper_price=Decimal("100"),
                lower_price=Decimal("100"),
                grid_count=5,
                investment_per_grid=Decimal("100"),
            )

    def test_upper_lower_than_lower_raises(self) -> None:
        with pytest.raises(ValidationError):
            GridCalculator.calculate_levels(
                upper_price=Decimal("50"),
                lower_price=Decimal("100"),
                grid_count=5,
                investment_per_grid=Decimal("100"),
            )

    def test_grid_count_must_be_at_least_2(self) -> None:
        with pytest.raises(ValidationError, match="grid_count must be >= 2"):
            GridCalculator.calculate_levels(
                upper_price=Decimal("100"),
                lower_price=Decimal("50"),
                grid_count=1,
                investment_per_grid=Decimal("100"),
            )

    def test_investment_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="investment_per_grid must be > 0"):
            GridCalculator.calculate_levels(
                upper_price=Decimal("100"),
                lower_price=Decimal("50"),
                grid_count=5,
                investment_per_grid=Decimal("0"),
            )


class TestGridCalculatorLevels:

    def test_generates_correct_number_of_levels(self) -> None:
        levels = GridCalculator.calculate_levels(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=10,
            investment_per_grid=Decimal("100"),
        )
        assert len(levels) == 10

    def test_levels_are_evenly_spaced(self) -> None:
        levels = GridCalculator.calculate_levels(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        spacing = Decimal("10")  # (100-50)/5 = 10
        for i, lv in enumerate(levels):
            expected_buy = Decimal("50") + spacing * Decimal(i)
            assert lv.buy_price == expected_buy
            expected_sell = expected_buy + spacing
            if expected_sell > Decimal("100"):
                expected_sell = Decimal("100")
            assert lv.sell_price == expected_sell

    def test_quantity_is_investment_divided_by_price(self) -> None:
        levels = GridCalculator.calculate_levels(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        for lv in levels:
            if lv.buy_price > 0:
                expected_qty = Decimal("100") / lv.buy_price
                assert lv.quantity == expected_qty

    def test_all_levels_start_waiting(self) -> None:
        levels = GridCalculator.calculate_levels(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        for lv in levels:
            assert lv.status == GridLevelStatus.WAITING

    def test_level_indices_are_sequential(self) -> None:
        levels = GridCalculator.calculate_levels(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        for i, lv in enumerate(levels):
            assert lv.level == i

    def test_spacing_calculation(self) -> None:
        spacing = GridCalculator.calculate_spacing(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
        )
        assert spacing == Decimal("10")

    def test_calculate_grid_state_data(self) -> None:
        data = GridCalculator.calculate_grid_state_data(
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=5,
            investment_per_grid=Decimal("100"),
        )
        assert "levels" in data
        assert "grid_spacing" in data
        assert len(data["levels"]) == 5
        assert data["grid_spacing"] == Decimal("10")
