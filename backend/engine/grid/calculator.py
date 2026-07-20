"""
GridCalculator — generates evenly-spaced grid levels from configuration.

This module is purely computational. It does not interact with the exchange,
the Execution Engine, or the Market Hub.
"""

from __future__ import annotations

from decimal import Decimal

from core.domain_types import GridLevel, GridLevelStatus
from core.exceptions import ValidationError


class GridCalculator:
    """Calculate grid levels from upper/lower price, grid count, and investment."""

    @staticmethod
    def validate_parameters(
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> None:
        if upper_price <= lower_price:
            raise ValidationError(
                f"upper_price ({upper_price}) must be > lower_price ({lower_price})"
            )
        if grid_count < 2:
            raise ValidationError(f"grid_count must be >= 2, got {grid_count}")
        if investment_per_grid <= 0:
            raise ValidationError(
                f"investment_per_grid must be > 0, got {investment_per_grid}"
            )

    @staticmethod
    def calculate_spacing(
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
    ) -> Decimal:
        """Evenly spaced interval between adjacent grid levels."""
        return (upper_price - lower_price) / Decimal(grid_count)

    @classmethod
    def calculate_levels(
        cls,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> list[GridLevel]:
        """Generate ``grid_count`` grid levels between lower and upper price.

        Each level ``i`` has:
        - buy_price  = lower + i * spacing  (the price at which we buy)
        - sell_price = buy_price + spacing   (the price at which we sell after buy fills)
        - quantity   = investment_per_grid / buy_price
        """
        cls.validate_parameters(
            upper_price, lower_price, grid_count, investment_per_grid
        )

        spacing = cls.calculate_spacing(upper_price, lower_price, grid_count)
        levels: list[GridLevel] = []

        for i in range(grid_count):
            buy_price = lower_price + spacing * Decimal(i)
            sell_price = buy_price + spacing
            if sell_price > upper_price:
                sell_price = upper_price
            quantity = (
                investment_per_grid / buy_price if buy_price > 0 else Decimal("0")
            )
            levels.append(
                GridLevel(
                    level=i,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    quantity=quantity,
                    status=GridLevelStatus.WAITING,
                )
            )
        return levels

    @classmethod
    def calculate_grid_state_data(
        cls,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> dict:
        """Return a dict with levels and spacing for GridState construction."""
        levels = cls.calculate_levels(
            upper_price, lower_price, grid_count, investment_per_grid
        )
        spacing = cls.calculate_spacing(upper_price, lower_price, grid_count)
        return {
            "levels": levels,
            "grid_spacing": spacing,
        }
