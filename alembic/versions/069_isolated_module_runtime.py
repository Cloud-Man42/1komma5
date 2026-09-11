"""069 — isolated module runtime (Step 5C.5)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "069_isolated_module_runtime"
down_revision = "068_marketplace_distribution_supply_chain"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _table_names()

    if "isolated_runtime_instances" not in tables:
        op.create_table(
            "isolated_runtime_instances",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("runtime_instance_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("module_id", sa.String(length=128), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("publisher_id", sa.String(length=128), nullable=False),
            sa.Column("artifact_sha256", sa.String(length=128), nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.Column("state", sa.String(length=32), nullable=False, server_default="BLOCKED"),
            sa.Column("process_identity", sa.String(length=128), nullable=True),
            sa.Column("process_pid", sa.Integer(), nullable=True),
            sa.Column("sandbox_mode", sa.String(length=32), nullable=True),
            sa.Column("socket_path", sa.Text(), nullable=True),
            sa.Column("package_path", sa.Text(), nullable=True),
            sa.Column("data_path", sa.Text(), nullable=True),
            sa.Column("protocol_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("reason_codes_json", sa.Text(), nullable=True),
            sa.Column("permissions_json", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_isolated_runtime_module_site", "isolated_runtime_instances", ["module_id", "site_id"])
        op.create_index("ix_isolated_runtime_state", "isolated_runtime_instances", ["state"])

    if "runtime_events" not in tables:
        op.create_table(
            "runtime_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("runtime_instance_id", sa.String(length=64), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("module_id", sa.String(length=128), nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_runtime_events_instance", "runtime_events", ["runtime_instance_id"])

    if "runtime_control_leases" not in tables:
        op.create_table(
            "runtime_control_leases",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("runtime_instance_id", sa.String(length=64), nullable=False),
            sa.Column("module_id", sa.String(length=128), nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.Column("device_id", sa.String(length=128), nullable=False),
            sa.Column("capability", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_runtime_leases_instance", "runtime_control_leases", ["runtime_instance_id"])


def downgrade() -> None:
    for table in ("runtime_control_leases", "runtime_events", "isolated_runtime_instances"):
        if table in _table_names():
            op.drop_table(table)
