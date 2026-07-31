"""Create strategy_modes table and seed default modes

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-29 00:00:00.000000

Previously the five strategy modes (A, B, C, D, U) lived only in a
hardcoded in-memory Python list (``STRATEGY_MODES_CONFIG`` in
``api.v1.endpoints.admin``). Admin edits via ``PUT /admin/strategy-modes``
mutated that list but were lost on every backend restart and were not
shared across Fly instances, so users never saw the changes.

This migration creates a ``strategy_modes`` table and seeds it with the
same five default rows so that admin edits persist in the database.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Must stay in sync with the DEFAULT_STRATEGY_MODES in
# services.strategy_mode_store and the former STRATEGY_MODES_CONFIG.
_DEFAULT_MODES = [
    ("A", "Steady",            0.0, 0.3, "Low",         0),
    ("B", "Conventional",      0.0, 0.6, "Medium",      1),
    ("C", "Aggressive",        0.0, 0.9, "High",        2),
    ("D", "Very Aggressive",   0.0, 1.5, "Very High",   3),
    ("U", "Ultimate",          0.0, 3.0, "Extreme",     4),
]


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "strategy_modes"):
        op.create_table(
            "strategy_modes",
            sa.Column("mode", sa.String(2), primary_key=True),
            sa.Column("label", sa.String(50), nullable=False),
            sa.Column("tp_range_min", sa.Float(), nullable=False, server_default="0"),
            sa.Column("tp_range_max", sa.Float(), nullable=False, server_default="0"),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="Medium"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # Seed default rows (idempotent — skip rows that already exist).
    existing = {row[0] for row in bind.execute(sa.text("SELECT mode FROM strategy_modes"))}
    for mode, label, tp_min, tp_max, risk, sort in _DEFAULT_MODES:
        if mode in existing:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO strategy_modes "
                "(mode, label, tp_range_min, tp_range_max, risk_level, is_active, sort_order) "
                "VALUES (:mode, :label, :tp_min, :tp_max, :risk, true, :sort)"
            ),
            {
                "mode": mode,
                "label": label,
                "tp_min": tp_min,
                "tp_max": tp_max,
                "risk": risk,
                "sort": sort,
            },
        )


def downgrade() -> None:
    op.drop_table("strategy_modes")
