"""077 — user site selection preferences + per-site battery capacity."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "077_user_site_prefs"
down_revision = "076_emic_user_auth"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "battery_usable_capacity_kwh" not in _column_names("sites"):
        op.add_column("sites", sa.Column("battery_usable_capacity_kwh", sa.Float(), nullable=True))

    if "emic_user_site_preferences" not in _table_names():
        op.create_table(
            "emic_user_site_preferences",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("emic_users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("selected_site_slugs", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    if "emic_user_site_preferences" in _table_names():
        op.drop_table("emic_user_site_preferences")
    if "battery_usable_capacity_kwh" in _column_names("sites"):
        op.drop_column("sites", "battery_usable_capacity_kwh")
