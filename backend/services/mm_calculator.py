"""
MMCalculator — Money Management calculation service.

Core formulas:
  buy_amount = capital / steps
  max_coins  = capital / buy_amount (= steps)

Validation rules:
  MM30: min_capital=$300, only for 3 Kings / 5 Kings / Top 5
  MM50: min_capital=$500, for Top 10 / Top 20
  MM70: min_capital=$700, for Top 20 / Top 50 / All
  Custom: user-defined steps, min_capital=$100 (Pro+ only)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.exceptions import ValidationError
from core.logging import get_logger

logger = get_logger(__name__)

BUILTIN_PRESETS = {
    "mm30": {
        "name": "MM30",
        "steps": 30,
        "min_capital": Decimal("300"),
        "max_capital": None,
        "description": "30-step money management — conservative, suitable for 3 Kings / 5 Kings",
        "allowed_coin_groups": ["3 Kings", "5 Kings"],
    },
    "mm50": {
        "name": "MM50",
        "steps": 50,
        "min_capital": Decimal("500"),
        "max_capital": None,
        "description": "50-step money management — balanced, suitable for Top 10 / Top 20",
        "allowed_coin_groups": ["Top 10", "Top 20"],
    },
    "mm70": {
        "name": "MM70",
        "steps": 70,
        "min_capital": Decimal("700"),
        "max_capital": None,
        "description": "70-step money management — aggressive, suitable for Top 20 / Top 50 / All",
        "allowed_coin_groups": ["Top 20", "Top 50", "All"],
    },
}


@dataclass
class MMCalculationResult:
    buy_amount: Decimal
    max_coins: int
    steps: int
    capital: Decimal
    preset_type: str
    min_volume_filter: Decimal


class MMCalculator:
    """Calculate buy amount, max coins, and volume filter from MM preset + capital."""

    def calculate(
        self,
        preset_type: str,
        capital: Decimal,
        coin_group_name: str | None = None,
        custom_steps: int | None = None,
    ) -> MMCalculationResult:
        preset_type = preset_type.lower()

        if preset_type == "custom":
            if custom_steps is None or custom_steps < 1:
                raise ValidationError("Custom preset requires custom_steps >= 1")
            if custom_steps > 200:
                raise ValidationError("Custom preset steps cannot exceed 200")
            steps = custom_steps
            min_capital = Decimal("100")
        else:
            preset = BUILTIN_PRESETS.get(preset_type)
            if preset is None:
                raise ValidationError(
                    f"Invalid preset type: {preset_type}. Must be one of {list(BUILTIN_PRESETS.keys())} or 'custom'"
                )
            steps = preset["steps"]
            min_capital = preset["min_capital"]

            if coin_group_name and preset.get("allowed_coin_groups"):
                if coin_group_name not in preset["allowed_coin_groups"]:
                    raise ValidationError(
                        f"Preset {preset_type} is only compatible with {preset['allowed_coin_groups']}, got '{coin_group_name}'"
                    )

        if capital < min_capital:
            raise ValidationError(
                f"Capital {capital} is below minimum {min_capital} for preset {preset_type}"
            )

        buy_amount = capital / Decimal(steps)
        max_coins = steps
        min_volume_filter = buy_amount * Decimal("10")

        logger.info(
            "MM calculation",
            extra={
                "preset_type": preset_type,
                "capital": str(capital),
                "buy_amount": str(buy_amount),
                "max_coins": max_coins,
            },
        )

        return MMCalculationResult(
            buy_amount=buy_amount,
            max_coins=max_coins,
            steps=steps,
            capital=capital,
            preset_type=preset_type,
            min_volume_filter=min_volume_filter,
        )

    def get_builtin_presets(self) -> list[dict]:
        return [
            {
                "preset_type": k,
                "name": v["name"],
                "steps": v["steps"],
                "min_capital": str(v["min_capital"]),
                "max_capital": str(v["max_capital"]) if v["max_capital"] else None,
                "description": v["description"],
                "allowed_coin_groups": v["allowed_coin_groups"],
            }
            for k, v in BUILTIN_PRESETS.items()
        ]
