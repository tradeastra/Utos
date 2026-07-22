"""Add technical_analysis_configs table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "technical_analysis_configs"):
        op.create_table(
            "technical_analysis_configs",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("trading_instance_id", sa.dialects.postgresql.UUID(as_uuid=True),
                       sa.ForeignKey("trading_instances.id", ondelete="CASCADE"), nullable=False),
            sa.Column("indicator", sa.String(50), nullable=False),
            sa.Column("time_frame", sa.String(10), nullable=False, server_default="1h"),
            sa.Column("operator", sa.String(10), nullable=False, server_default="and"),
            sa.Column("params", sa.dialects.postgresql.JSONB, nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("idx_ta_configs_instance_id", "technical_analysis_configs", ["trading_instance_id"])


def downgrade() -> None:
    op.drop_index("idx_ta_configs_instance_id", table_name="technical_analysis_configs")
    op.drop_table("technical_analysis_configs")
