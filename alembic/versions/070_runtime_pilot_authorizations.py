"""070 — per-module runtime pilot authorizations (Sprint E)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "070_runtime_pilot_authorizations"
down_revision = "069_isolated_module_runtime"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "runtime_pilot_authorizations" in _table_names():
        return
    op.create_table(
        "runtime_pilot_authorizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=128), nullable=False),
        sa.Column("publisher_id", sa.String(length=128), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_runtime_pilot_auth_lookup",
        "runtime_pilot_authorizations",
        ["module_id", "version", "artifact_sha256", "publisher_id", "site_id"],
    )
    op.create_index("ix_runtime_pilot_auth_site", "runtime_pilot_authorizations", ["site_id"])


def downgrade() -> None:
    if "runtime_pilot_authorizations" in _table_names():
        op.drop_table("runtime_pilot_authorizations")
