"""071 — climate device readings (Sprint E)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "071_climate_device_state"
down_revision = "070_runtime_pilot_authorizations"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "climate_device_readings" in _table_names():
        return
    op.create_table(
        "climate_device_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("external_device_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_climate_readings_site_device",
        "climate_device_readings",
        ["site_id", "external_device_id"],
        unique=True,
    )


def downgrade() -> None:
    if "climate_device_readings" in _table_names():
        op.drop_table("climate_device_readings")
