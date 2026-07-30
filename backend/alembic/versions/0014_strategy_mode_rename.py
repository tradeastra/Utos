"""Rename strategy modes (A=Hyper, B=Aggressive, C=Balanced) and deactivate D, U

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-30 00:00:00.000000

The previous labels were backwards: mode A (0.3% spacing, most frequent
trades) was labelled "Steady/Conservative" while mode U (3.0% spacing,
rarest trades) was labelled "Ultimate/Speculative". Tight spacing means
MORE aggressive trading, not less.

This migration:
  - Renames A → "Hyper" (Very Aggressive), B → "Aggressive", C → "Balanced"
  - Updates risk_level and description for A, B, C
  - Deactivates D and U (is_active = false) — spacing 1.5%+ is too wide
    for an autotrading bot whose goal is frequent trades. Existing
    trading instances that reference D/U still work (the enum value is
    preserved), but new setups only offer A/B/C.
  - TP per level = spacing × 2.5 (applied in GridCalculator, not here).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (mode, label, risk_level, description)
_UPDATES = [
    (
        "A",
        "Hyper",
        "Very Aggressive",
        "Tightest grid (0.3% spacing). Maximum trade frequency — many small "
        "profits, fast capital rotation. Best for ranging markets. "
        "TP 0.75% per level.",
    ),
    (
        "B",
        "Aggressive",
        "Aggressive",
        "Tight grid (0.6% spacing). High trade frequency with moderate profit "
        "per level. Good for normal volatility. TP 1.5% per level.",
    ),
    (
        "C",
        "Balanced",
        "Balanced",
        "Moderate grid (0.9% spacing). Balanced trade frequency and profit. "
        "General-purpose mode. TP 2.25% per level.",
    ),
]

# Modes to deactivate (spacing too wide for frequent trading).
_DEACTIVATE = ["D", "U"]


def upgrade() -> None:
    bind = op.get_bind()
    for mode, label, risk_level, description in _UPDATES:
        bind.execute(
            sa.text(
                "UPDATE strategy_modes "
                "SET label = :label, risk_level = :risk, description = :desc "
                "WHERE mode = :mode"
            ),
            {
                "mode": mode,
                "label": label,
                "risk": risk_level,
                "desc": description,
            },
        )
    for mode in _DEACTIVATE:
        bind.execute(
            sa.text(
                "UPDATE strategy_modes SET is_active = false WHERE mode = :mode"
            ),
            {"mode": mode},
        )


def downgrade() -> None:
    bind = op.get_bind()
    # Restore old labels for A, B, C
    _OLD = [
        ("A", "Steady", "Conservative",
         "Tight grid (0.3% spacing). Frequent trades, fast capital rotation, "
         "quick drawdown recovery. Best for ranging/sideways markets."),
        ("B", "Conventional", "Balanced",
         "Moderate grid (0.6% spacing). Balanced trade frequency and profit "
         "per level. General-purpose mode for most market conditions."),
        ("C", "Aggressive", "Active",
         "Wider grid (0.9% spacing). Fewer trades, larger profit each. "
         "Needs moderate volatility to stay active."),
    ]
    for mode, label, risk_level, description in _OLD:
        bind.execute(
            sa.text(
                "UPDATE strategy_modes "
                "SET label = :label, risk_level = :risk, description = :desc "
                "WHERE mode = :mode"
            ),
            {
                "mode": mode,
                "label": label,
                "risk": risk_level,
                "desc": description,
            },
        )
    for mode in _DEACTIVATE:
        bind.execute(
            sa.text(
                "UPDATE strategy_modes SET is_active = true WHERE mode = :mode"
            ),
            {"mode": mode},
        )
