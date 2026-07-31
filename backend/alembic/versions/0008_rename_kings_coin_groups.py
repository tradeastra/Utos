"""Rename built-in coin groups '3 Kings'->'Top 3', '5 Kings'->'Top 5'

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-26 00:00:00.000000

Also updates mm_presets.allowed_coin_groups JSON arrays that referenced the
old names so MM30 compatibility validation keeps working.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RENAMES = [("3 Kings", "Top 3"), ("5 Kings", "Top 5")]


def upgrade() -> None:
    # --- Rename built-in coin_groups rows ---
    for old_name, new_name in _RENAMES:
        op.execute(
            f"UPDATE coin_groups SET name = '{new_name}' "
            f"WHERE name = '{old_name}' AND is_builtin = true"
        )

    # --- Update mm_presets.allowed_coin_groups JSON arrays ---
    # PostgreSQL jsonb replace for the renamed entries.
    for old_name, new_name in _RENAMES:
        op.execute(
            f"UPDATE mm_presets "
            f"SET allowed_coin_groups = REPLACE(allowed_coin_groups::text, "
            f"'\"{old_name}\"', '\"{new_name}\"')::jsonb "
            f"WHERE allowed_coin_groups::text LIKE '%\"{old_name}\"%'"
        )


def downgrade() -> None:
    for new_name, old_name in _RENAMES:
        op.execute(
            f"UPDATE coin_groups SET name = '{old_name}' "
            f"WHERE name = '{new_name}' AND is_builtin = true"
        )
        op.execute(
            f"UPDATE mm_presets "
            f"SET allowed_coin_groups = REPLACE(allowed_coin_groups::text, "
            f"'\"{new_name}\"', '\"{old_name}\"')::jsonb "
            f"WHERE allowed_coin_groups::text LIKE '%\"{new_name}\"%'"
        )
