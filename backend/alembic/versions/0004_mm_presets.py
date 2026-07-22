"""Add mm_presets table + mm_preset_id/capital to trading_instances

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- Create mm_presets table (idempotent) ---
    if not bind.dialect.has_table(bind, "mm_presets"):
        op.create_table(
            "mm_presets",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("preset_type", sa.String(20), nullable=False),
            sa.Column("steps", sa.Integer(), nullable=False),
            sa.Column("min_capital", sa.Numeric(20, 8), nullable=False),
            sa.Column("max_capital", sa.Numeric(20, 8), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("allowed_coin_groups", sa.JSON(), nullable=True),
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("idx_mm_presets_user_id", "mm_presets", ["user_id"])
        op.create_index("idx_mm_presets_preset_type", "mm_presets", ["preset_type"])
        op.create_index("idx_mm_presets_is_builtin", "mm_presets", ["is_builtin"])

    # --- Add columns to trading_instances (idempotent) ---
    existing_cols = {row[0] for row in bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'trading_instances'")
    )}
    if "mm_preset_id" not in existing_cols:
        op.add_column(
            "trading_instances",
            sa.Column("mm_preset_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("mm_presets.id"), nullable=True),
        )
    if "capital" not in existing_cols:
        op.add_column(
            "trading_instances",
            sa.Column("capital", sa.Numeric(20, 8), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("trading_instances", "capital")
    op.drop_column("trading_instances", "mm_preset_id")

    op.drop_index("idx_mm_presets_is_builtin", table_name="mm_presets")
    op.drop_index("idx_mm_presets_preset_type", table_name="mm_presets")
    op.drop_index("idx_mm_presets_user_id", table_name="mm_presets")
    op.drop_table("mm_presets")
