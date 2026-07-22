"""Add averaging_configs table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "averaging_configs"):
        op.create_table(
            "averaging_configs",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("trading_instance_id", sa.dialects.postgresql.UUID(as_uuid=True),
                       sa.ForeignKey("trading_instances.id", ondelete="CASCADE"), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("drop_rate", sa.Numeric(8, 4), nullable=False),
            sa.Column("multiple_buy_amount", sa.Numeric(10, 4), nullable=False, server_default="1.0"),
            sa.Column("take_profit", sa.Numeric(8, 4), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("trading_instance_id", "step_number", name="uq_avg_config_instance_step"),
        )
        op.create_index("idx_averaging_configs_instance_id", "averaging_configs", ["trading_instance_id"])


def downgrade() -> None:
    op.drop_index("idx_averaging_configs_instance_id", table_name="averaging_configs")
    op.drop_table("averaging_configs")
