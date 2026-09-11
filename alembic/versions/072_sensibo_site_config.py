"""072 — external module site config extensions (Sprint E)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "072_sensibo_site_config"
down_revision = "071_climate_device_state"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "external_module_site_configs" in _table_names():
        return
    op.create_table(
        "external_module_site_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("credential_ref", sa.String(length=128), nullable=False, server_default="api_key"),
        sa.Column("credential_encrypted", sa.Text(), nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("selected_device_ids_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("site_id", "module_id", name="uq_external_module_site"),
    )


def downgrade() -> None:
    if "external_module_site_configs" in _table_names():
        op.drop_table("external_module_site_configs")
