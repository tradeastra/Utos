"""
Default averaging configuration template — 35 steps with Moonbot pattern.

Drop rates (%): 0.6, 1.2, 1.1, 1.0, 2.0, repeating with slight variations.
Take profit (%): 1.5 for early steps, 2.0 for mid, 3.0 for deep steps.
Multiple buy amount: 1.0x for first 5 steps, 1.5x for steps 6-15, 2.0x for steps 16-35.
"""

from decimal import Decimal

# Moonbot-style 35-step drop rate pattern (percent)
DEFAULT_DROP_RATES = [
    0.6, 1.2, 1.1, 1.0, 2.0,
    0.8, 1.5, 1.3, 1.1, 2.5,
    1.0, 1.8, 1.5, 1.2, 3.0,
    1.2, 2.0, 1.8, 1.5, 3.5,
    1.5, 2.5, 2.0, 1.8, 4.0,
    1.8, 3.0, 2.5, 2.0, 4.5,
    2.0, 3.5, 3.0, 2.5, 5.0,
]

DEFAULT_TAKE_PROFITS = [
    1.5, 1.5, 1.5, 1.5, 2.0,
    1.5, 1.5, 2.0, 2.0, 2.0,
    2.0, 2.0, 2.5, 2.5, 2.5,
    2.5, 2.5, 3.0, 3.0, 3.0,
    3.0, 3.0, 3.5, 3.5, 3.5,
    3.5, 4.0, 4.0, 4.0, 4.5,
    4.5, 5.0, 5.0, 5.5, 6.0,
]

DEFAULT_MULTIPLIERS = [
    1.0, 1.0, 1.0, 1.0, 1.0,     # steps 1-5: base
    1.5, 1.5, 1.5, 1.5, 1.5,     # steps 6-10: 1.5x
    1.5, 1.5, 1.5, 1.5, 1.5,     # steps 11-15: 1.5x
    2.0, 2.0, 2.0, 2.0, 2.0,     # steps 16-20: 2x
    2.0, 2.0, 2.0, 2.0, 2.0,     # steps 21-25: 2x
    2.0, 2.0, 2.0, 2.0, 2.0,     # steps 26-30: 2x
    2.5, 2.5, 2.5, 2.5, 3.0,     # steps 31-35: 2.5-3x
]


def get_default_averaging_template() -> list[dict]:
    """Return the default 35-step averaging configuration template."""
    return [
        {
            "step_number": i,
            "drop_rate": Decimal(str(DEFAULT_DROP_RATES[i])),
            "multiple_buy_amount": Decimal(str(DEFAULT_MULTIPLIERS[i])),
            "take_profit": Decimal(str(DEFAULT_TAKE_PROFITS[i])),
        }
        for i in range(35)
    ]


def get_default_averaging_summary() -> dict:
    """Return summary stats for the default template."""
    return {
        "total_steps": 35,
        "avg_drop_rate": sum(DEFAULT_DROP_RATES) / len(DEFAULT_DROP_RATES),
        "max_drop_rate": max(DEFAULT_DROP_RATES),
        "min_drop_rate": min(DEFAULT_DROP_RATES),
        "avg_take_profit": sum(DEFAULT_TAKE_PROFITS) / len(DEFAULT_TAKE_PROFITS),
        "max_multiplier": max(DEFAULT_MULTIPLIERS),
        "drop_rates": DEFAULT_DROP_RATES,
        "take_profits": DEFAULT_TAKE_PROFITS,
        "multipliers": DEFAULT_MULTIPLIERS,
    }
