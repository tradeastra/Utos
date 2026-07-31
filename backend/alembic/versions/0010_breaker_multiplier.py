"""Drop future_drop_multiplier, set tier-based min_future_drop_pct defaults

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-28 12:00:00.000000

Removes the ``future_drop_multiplier`` column (replaced by fixed per-tier
``min_future_drop_pct`` values) and updates existing rows to use the new
tier defaults:
  - rate 0.70 → window=5,  future_drop=9%
  - rate 0.80 → window=10, future_drop=12%
  - rate 0.90 → window=30, future_drop=15%
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the multiplier column if it exists (added by a previous draft).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("breaker_thresholds")]
    if "future_drop_multiplier" in columns:
        op.drop_column("breaker_thresholds", "future_drop_multiplier")

    # Update existing rows to tier-based window + future_drop defaults.
    op.execute(
        "UPDATE breaker_thresholds SET continuation_window=5, "
        "min_future_drop_pct=9.0 WHERE min_continuation_rate=0.70"
    )
    op.execute(
        "UPDATE breaker_thresholds SET continuation_window=10, "
        "min_future_drop_pct=12.0 WHERE min_continuation_rate=0.80"
    )
    op.execute(
        "UPDATE breaker_thresholds SET continuation_window=30, "
        "min_future_drop_pct=15.0 WHERE min_continuation_rate=0.90"
    )

    # Change column default to 9.0 (Protective tier default).
    op.alter_column(
        "breaker_thresholds",
        "min_future_drop_pct",
        server_default="9.0",
    )


def downgrade() -> None:
    op.alter_column(
        "breaker_thresholds",
        "min_future_drop_pct",
        server_default="3.0",
    )
    op.add_column(
        "breaker_thresholds",
        sa.Column(
            "future_drop_multiplier",
            sa.Numeric(precision=3, scale=1),
            nullable=False,
            server_default="3.0",
        ),
    )
