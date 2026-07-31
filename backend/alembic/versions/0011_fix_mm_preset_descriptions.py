"""Fix built-in mm_presets.description still referencing old 'Kings' labels

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-29 00:00:00.000000

Migration 0008 renamed coin_groups '3 Kings'->'Top 3' / '5 Kings'->'Top 5'
and updated mm_presets.allowed_coin_groups, but did NOT update
mm_presets.description. Built-in rows seeded before 0008 therefore still
show "suitable for 3 Kings / 5 Kings" in their description text.

This migration rewrites the description (and allowed_coin_groups, as a
safety net) for every built-in preset to match the current source of
truth in services.mm_calculator.BUILTIN_PRESETS.
"""

import json
from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Must stay in sync with services.mm_calculator.BUILTIN_PRESETS.
_PRESETS = {
    "mm30": {
        "description": "30-step money management — conservative, suitable for Top 3 / Top 5",
        "allowed_coin_groups": ["Top 3", "Top 5"],
    },
    "mm50": {
        "description": "50-step money management — balanced, suitable for Top 10 / Top 20",
        "allowed_coin_groups": ["Top 10", "Top 20"],
    },
    "mm70": {
        "description": "70-step money management — aggressive, suitable for Top 20 / Top 50 / All",
        "allowed_coin_groups": ["Top 20", "Top 50", "All"],
    },
}


def upgrade() -> None:
    for preset_type, data in _PRESETS.items():
        desc_escaped = data["description"].replace("'", "''")
        groups_json = json.dumps(data["allowed_coin_groups"])
        op.execute(
            f"UPDATE mm_presets "
            f"SET description = '{desc_escaped}', "
            f"allowed_coin_groups = '{groups_json}'::jsonb "
            f"WHERE preset_type = '{preset_type}' AND is_builtin = true"
        )


def downgrade() -> None:
    # No-op: the old description text referenced deprecated 'Kings' labels
    # and should not be restored.
    pass
