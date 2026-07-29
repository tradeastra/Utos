"""Add resume_mode, recovery_pct, widen_multiplier to breaker_thresholds

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-29 13:00:00.000000

Adds three columns to ``breaker_thresholds`` that control what the bot does
AFTER the circuit breaker triggers (the resume behavior):

  - resume_mode (str, default "ta_confirm"): one of "ta_confirm",
    "widen_step", "trailing_buy". See ``BreakerResumeMode`` enum.
  - recovery_pct (numeric, default 5.0): for "trailing_buy" mode — the %
    recovery from the intraday low required before buys resume.
  - widen_multiplier (numeric, default 2.0): for "widen_step" mode — the
    grid step multiplier while the breaker is active (2 = 2× wider spacing).

All three default to the legacy behavior (ta_confirm / 5% / 2×) so existing
rows keep working unchanged.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "breaker_thresholds",
        sa.Column(
            "resume_mode",
            sa.String(length=20),
            nullable=False,
            server_default="ta_confirm",
        ),
    )
    op.add_column(
        "breaker_thresholds",
        sa.Column(
            "recovery_pct",
            sa.Numeric(precision=4, scale=2),
            nullable=False,
            server_default="5.0",
        ),
    )
    op.add_column(
        "breaker_thresholds",
        sa.Column(
            "widen_multiplier",
            sa.Numeric(precision=3, scale=1),
            nullable=False,
            server_default="2.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("breaker_thresholds", "widen_multiplier")
    op.drop_column("breaker_thresholds", "recovery_pct")
    op.drop_column("breaker_thresholds", "resume_mode")
