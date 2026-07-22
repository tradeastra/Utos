"""Add coin_groups table + strategy_mode/selected_coins to trading_instances

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Create strategy_mode enum (PostgreSQL doesn't support IF NOT EXISTS for CREATE TYPE) ---
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE strategy_mode_enum AS ENUM "
        "('super_bearish', 'conventional', 'aggressive', 'very_aggressive', 'ultimate'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    # --- Add columns to trading_instances (idempotent) ---
    bind = op.get_bind()
    existing_cols = {row[0] for row in bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'trading_instances'")
    )}
    if "strategy_mode" not in existing_cols:
        op.add_column(
            "trading_instances",
            sa.Column("strategy_mode", sa.Enum(
                "super_bearish", "conventional", "aggressive", "very_aggressive", "ultimate",
                name="strategy_mode_enum",
            ), nullable=True),
        )
    if "selected_coins" not in existing_cols:
        op.add_column(
            "trading_instances",
            sa.Column("selected_coins", sa.JSON(), nullable=True),
        )

    # --- Create coin_groups table (idempotent) ---
    if not bind.dialect.has_table(bind, "coin_groups"):
        op.create_table(
            "coin_groups",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("max_coins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("coins", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("idx_coin_groups_user_id", "coin_groups", ["user_id"])
        op.create_index("idx_coin_groups_is_builtin", "coin_groups", ["is_builtin"])


def downgrade() -> None:
    op.drop_index("idx_coin_groups_is_builtin", table_name="coin_groups")
    op.drop_index("idx_coin_groups_user_id", table_name="coin_groups")
    op.drop_table("coin_groups")

    op.drop_column("trading_instances", "selected_coins")
    op.drop_column("trading_instances", "strategy_mode")

    op.execute("DROP TYPE IF EXISTS strategy_mode_enum")
