"""
ProfitCalculator — calculates floating profit from position data and current price.

Pure computation, no side effects, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.exceptions import ValidationError


@dataclass
class ProfitResult:
    """Result of a profit calculation."""

    floating_profit: Decimal
    profit_percentage: Decimal
    is_profitable: bool
    entry_price: Decimal
    current_price: Decimal
    quantity: Decimal


class ProfitCalculator:
    """Calculate floating profit for long and short positions."""

    @staticmethod
    def validate(
        entry_price: Decimal, current_price: Decimal, quantity: Decimal
    ) -> None:
        if entry_price <= 0:
            raise ValidationError(f"entry_price must be > 0, got {entry_price}")
        if current_price <= 0:
            raise ValidationError(f"current_price must be > 0, got {current_price}")
        if quantity <= 0:
            raise ValidationError(f"quantity must be > 0, got {quantity}")

    @classmethod
    def calculate(
        cls,
        entry_price: Decimal,
        current_price: Decimal,
        quantity: Decimal,
        side: str,
    ) -> ProfitResult:
        """Calculate floating profit and profit percentage.

        Args:
            entry_price: Average entry price of the position.
            current_price: Latest market price.
            quantity: Position size.
            side: "long" or "short".

        Returns:
            ProfitResult with floating_profit, profit_percentage, is_profitable.
        """
        cls.validate(entry_price, current_price, quantity)

        if side == "long":
            floating_profit = (current_price - entry_price) * quantity
        elif side == "short":
            floating_profit = (entry_price - current_price) * quantity
        else:
            raise ValidationError(f"side must be 'long' or 'short', got '{side}'")

        investment = entry_price * quantity
        profit_percentage = (
            (floating_profit / investment) * Decimal("100")
            if investment > 0
            else Decimal("0")
        )

        return ProfitResult(
            floating_profit=floating_profit,
            profit_percentage=profit_percentage,
            is_profitable=floating_profit > 0,
            entry_price=entry_price,
            current_price=current_price,
            quantity=quantity,
        )
