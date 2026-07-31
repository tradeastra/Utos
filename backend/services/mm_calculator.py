"""
MMCalculator — Money Management calculation service.

Core formulas (per-coin DCA/averaging model):
  steps       = preset steps (MM30=30, MM50=50, MM70=70) — averaging layers PER COIN
  num_coins   = coin_group.max_coins (3, 5, 10, 20, 50, 999 for All)
  buy_amount  = capital / (steps * num_coins)            — base amount per DCA layer
  max_coins   = num_coins                                — from the selected coin group
  min_volume  = buy_amount * 10                          — 24h volume filter per coin

Each coin receives `steps` DCA layers of `buy_amount` each, so the total deployed
capital when every coin reaches its full averaging ladder is:
  total = buy_amount * steps * num_coins = capital

Validation rules:
  MM30: min_capital=$1,350, only for Top 3 / Top 5
  MM50: min_capital=$7,500, for Top 10 / Top 20
  MM70: min_capital=$21,000, for Top 20 / Top 50 / All
  Custom: user-defined steps, min_capital=$100 (Pro+ only)
  All presets: buy_amount must be >= MIN_BUY_AMOUNT ($15)

min_capital for built-in presets is derived from the smallest allowed coin
group: MIN_BUY_AMOUNT × steps × max_coins. This guarantees the per-layer buy
amount is at least $15 when using the smallest group, so the capital check
catches insufficient capital early with a clear message. Larger coin groups
may still fail the buy_amount check if capital is at the bare minimum.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from core.exceptions import ValidationError
from core.logging import get_logger

logger = get_logger(__name__)

MIN_BUY_AMOUNT = Decimal("15")

BUILTIN_PRESETS = {
    "mm30": {
        "name": "MM30",
        "steps": 30,
        "min_capital": Decimal("1350"),
        "max_capital": None,
<<<<<<< HEAD
        "description": "30-step money management — conservative",
        "allowed_coin_groups": [],
=======
        "description": "30-step money management — conservative, suitable for Top 3 / Top 5",
        "allowed_coin_groups": ["Top 3", "Top 5"],
>>>>>>> develop
    },
    "mm50": {
        "name": "MM50",
        "steps": 50,
        "min_capital": Decimal("7500"),
        "max_capital": None,
        "description": "50-step money management — balanced",
        "allowed_coin_groups": [],
    },
    "mm70": {
        "name": "MM70",
        "steps": 70,
        "min_capital": Decimal("21000"),
        "max_capital": None,
        "description": "70-step money management — aggressive",
        "allowed_coin_groups": [],
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
    """Calculate buy amount, max coins, and volume filter from MM preset + capital.

    The coin group's `max_coins` is REQUIRED because each coin receives `steps`
    DCA layers, so the per-layer buy amount depends on how many coins are traded.
    """

    def calculate(
        self,
        preset_type: str,
        capital: Decimal,
        coin_group_name: str | None = None,
        coin_group_max_coins: int | None = None,
        custom_steps: int | None = None,
        num_coins: int | None = None,
    ) -> MMCalculationResult:
        """Calculate buy amount, max coins, and volume filter.

        ``num_coins`` (if provided) overrides ``coin_group_max_coins`` — this
        lets the user trade fewer coins than the group's maximum (e.g. pick
        only BTC from Top 3) and get a larger per-layer buy amount.
        """
        preset_type = preset_type.lower()

        if coin_group_max_coins is None or coin_group_max_coins < 1:
            raise ValidationError(
                "coin_group_max_coins is required and must be >= 1 — "
                "each coin receives `steps` DCA layers, so the coin group size "
                "determines the per-layer buy amount."
            )
        # User-selected coin count overrides the group max — trading 1 coin
        # from Top 3 should allocate capital for 1 coin, not 3.
        effective_coins = num_coins if (num_coins and num_coins >= 1) else coin_group_max_coins

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

<<<<<<< HEAD
=======
            if coin_group_name and preset.get("allowed_coin_groups"):
                if coin_group_name not in preset["allowed_coin_groups"]:
                    raise ValidationError(
                        f"Preset {preset_type} is only compatible with {preset['allowed_coin_groups']}, got '{coin_group_name}'"
                    )

        # Adjust min_capital for the actual number of coins selected.
        # The preset's min_capital is derived from the smallest allowed group,
        # but if the user trades fewer coins, the real minimum is lower:
        #   min_capital = MIN_BUY_AMOUNT × steps × effective_coins
        if num_coins and num_coins >= 1 and num_coins < coin_group_max_coins:
            min_capital = MIN_BUY_AMOUNT * Decimal(steps) * Decimal(effective_coins)

>>>>>>> develop
        if capital < min_capital:
            raise ValidationError(
                f"Capital {capital} is below minimum {min_capital} for preset {preset_type} "
                f"({steps} steps × {effective_coins} coins × ${MIN_BUY_AMOUNT}/layer)"
            )

        # Per-layer buy amount: capital spread across (steps layers * effective_coins coins).
        buy_amount = (capital / (Decimal(steps) * Decimal(effective_coins))).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        max_coins = effective_coins
        min_volume_filter = buy_amount * Decimal("10")

        if buy_amount < MIN_BUY_AMOUNT:
            required = MIN_BUY_AMOUNT * Decimal(steps) * Decimal(effective_coins)
            raise ValidationError(
                f"Per-layer buy amount {buy_amount} is below minimum {MIN_BUY_AMOUNT}. "
                f"With {steps} steps × {effective_coins} coins, capital must be at least "
                f"${required} for preset {preset_type}."
            )

        logger.info(
            "MM calculation",
            extra={
                "preset_type": preset_type,
                "capital": str(capital),
                "buy_amount": str(buy_amount),
                "max_coins": max_coins,
                "steps": steps,
                "num_coins": effective_coins,
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
