"""Add per-coin settings columns to trading_instances

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trading_instances", sa.Column("avg_enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("trading_instances", sa.Column("non_stop", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("trading_instances", sa.Column("partial_sell", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("trading_instances", sa.Column("formula_mode", sa.String(50), nullable=False, server_default="default"))


def downgrade() -> None:
    op.drop_column("trading_instances", "formula_mode")
    op.drop_column("trading_instances", "partial_sell")
    op.drop_column("trading_instances", "non_stop")
    op.drop_column("trading_instances", "avg_enabled")
