"""Add continuation_rate, breaker_enabled to trading_instances

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-30 00:00:00.000000

Adds two columns to ``trading_instances`` so the circuit breaker
config chosen by the user in the setup wizard is persisted:

  - continuation_rate (numeric, nullable): 0.70 / 0.80 / 0.90 — selects
    which breaker threshold tier to use for this instance.
  - breaker_enabled (boolean, default true): master toggle.

These are read by ``setup_breaker_for_instance`` during ``start()`` to
install the circuit breaker with the correct threshold + resume mode.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "trading_instances"):
        return
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("trading_instances")}
    if "continuation_rate" not in cols:
        op.add_column(
            "trading_instances",
            sa.Column("continuation_rate", sa.Numeric(3, 2), nullable=True),
        )
    if "breaker_enabled" not in cols:
        op.add_column(
            "trading_instances",
            sa.Column(
                "breaker_enabled",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("trading_instances")}
    if "breaker_enabled" in cols:
        op.drop_column("trading_instances", "breaker_enabled")
    if "continuation_rate" in cols:
        op.drop_column("trading_instances", "continuation_rate")
