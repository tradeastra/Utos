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
    """Calculate grid levels from upper/lower price, grid count, and investment.

    Take-profit multiplier: sell price = buy price + spacing × 2.5.
    This gives 2.5× the grid spacing as profit per level, so tighter
    grids still earn meaningful profit per trade.
    """

    TP_MULTIPLIER = Decimal("2.5")

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
        - sell_price = buy_price + spacing × 2.5  (TP = 2.5× grid spacing)
        - quantity   = investment_per_grid / buy_price
        """
        cls.validate_parameters(
            upper_price, lower_price, grid_count, investment_per_grid
        )

        spacing = cls.calculate_spacing(upper_price, lower_price, grid_count)
        levels: list[GridLevel] = []

        for i in range(grid_count):
            buy_price = lower_price + spacing * Decimal(i)
            sell_price = buy_price + spacing * cls.TP_MULTIPLIER
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

    @classmethod
    def calculate_levels_with_averaging(
        cls,
        start_price: Decimal,
        investment_per_grid: Decimal,
        averaging_steps: list[dict],
    ) -> list[GridLevel]:
        """Generate grid levels using per-step drop rates from averaging config.

        Each step in ``averaging_steps`` should have:
        - step_number: int (0-indexed)
        - drop_rate: Decimal (percentage drop from previous level price)
        - multiple_buy_amount: Decimal (multiplier for investment at this step)
        - take_profit: Decimal (percentage gain for sell price)

        Step 0 buys at start_price. Step N buys at:
            buy_price = prev_buy_price * (1 - drop_rate_N / 100)
            sell_price = buy_price * (1 + take_profit_N / 100)
            quantity = (investment_per_grid * multiplier) / buy_price
        """
        if not averaging_steps:
            raise ValidationError("averaging_steps must not be empty")
        if investment_per_grid <= 0:
            raise ValidationError(
                f"investment_per_grid must be > 0, got {investment_per_grid}"
            )
        if start_price <= 0:
            raise ValidationError(
                f"start_price must be > 0, got {start_price}"
            )

        levels: list[GridLevel] = []
        prev_buy_price = start_price

        for step in averaging_steps:
            step_num = step["step_number"]
            drop_rate = step["drop_rate"]
            multiplier = step.get("multiple_buy_amount", Decimal("1.0"))
            take_profit = step["take_profit"]

            if step_num == 0:
                buy_price = start_price
            else:
                buy_price = prev_buy_price * (Decimal("1") - drop_rate / Decimal("100"))
                if buy_price <= 0:
                    raise ValidationError(
                        f"Step {step_num}: buy_price dropped to <= 0 (drop_rate={drop_rate}%)"
                    )

            sell_price = buy_price * (Decimal("1") + take_profit / Decimal("100"))
            step_investment = investment_per_grid * multiplier
            quantity = step_investment / buy_price if buy_price > 0 else Decimal("0")

            levels.append(
                GridLevel(
                    level=step_num,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    quantity=quantity,
                    status=GridLevelStatus.WAITING,
                )
            )
            prev_buy_price = buy_price

        return levels

    @classmethod
    def calculate_grid_state_data_with_averaging(
        cls,
        start_price: Decimal,
        investment_per_grid: Decimal,
        averaging_steps: list[dict],
    ) -> dict:
        """Return grid state data using per-step averaging config."""
        levels = cls.calculate_levels_with_averaging(
            start_price, investment_per_grid, averaging_steps
        )
        return {
            "levels": levels,
            "grid_spacing": Decimal("0"),  # Non-uniform spacing when using averaging
        }
