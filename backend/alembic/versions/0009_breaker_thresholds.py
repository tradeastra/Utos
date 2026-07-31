"""Add breaker_thresholds table — pre-computed circuit breaker thresholds

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-28 00:00:00.000000

Stores the per-symbol critical drop threshold derived by
CircuitBreakerScreener / DailyDropAnalyzer. This is the app's "source of
truth" — when a user applies a strategy, the grid engine reads the threshold
from here instead of re-analyzing historical candles each time.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from database.base import GUID

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "breaker_thresholds",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("exchange", sa.String(30), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("min_continuation_rate", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("threshold_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("continuation_window", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("min_future_drop_pct", sa.Numeric(precision=5, scale=2), nullable=False, server_default="3.0"),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("candle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_fallback", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("screened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ux_breaker_thresholds_key",
        "breaker_thresholds",
        ["exchange", "symbol", "min_continuation_rate"],
        unique=True,
    )
    op.create_index(
        "idx_breaker_thresholds_symbol",
        "breaker_thresholds",
        ["symbol"],
    )


def downgrade() -> None:
    op.drop_index("idx_breaker_thresholds_symbol", table_name="breaker_thresholds")
    op.drop_index("ux_breaker_thresholds_key", table_name="breaker_thresholds")
    op.drop_table("breaker_thresholds")
