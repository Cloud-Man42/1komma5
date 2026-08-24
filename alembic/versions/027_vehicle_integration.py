"""Vehicle integration tables."""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "027_vehicle_integration"
down_revision = "026_drop_required_energy_kwh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_provider_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="mercedes"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("region", sa.String(length=32), nullable=False, server_default="Europe"),
        sa.Column("username", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("encrypted_password", sa.Text(), nullable=False, server_default=""),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False, server_default=""),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False, server_default=""),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_guid", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("session_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("connection_state", sa.String(length=32), nullable=False, server_default="DISCONNECTED"),
        sa.Column("commands_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_error", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconnect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("http_429_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decode_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "provider", name="uq_vehicle_provider_connections_site_provider"),
    )
    op.create_index("ix_vehicle_provider_connections_site_id", "vehicle_provider_connections", ["site_id"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="mercedes"),
        sa.Column("external_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("vin", sa.String(length=32), nullable=True),
        sa.Column("manufacturer", sa.String(length=64), nullable=False, server_default="Mercedes-Benz"),
        sa.Column("model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("charger_id", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "provider", "external_id", name="uq_vehicles_site_provider_external"),
    )
    op.create_index("ix_vehicles_site_id", "vehicles", ["site_id"])

    op.create_table(
        "vehicle_capabilities",
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="discovery"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vehicle_id", "capability"),
    )

    op.create_table(
        "vehicle_state_latest",
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("state_of_charge_percent", sa.Float(), nullable=True),
        sa.Column("target_soc_percent", sa.Float(), nullable=True),
        sa.Column("electric_range_km", sa.Float(), nullable=True),
        sa.Column("is_plugged_in", sa.Boolean(), nullable=True),
        sa.Column("is_charging", sa.Boolean(), nullable=True),
        sa.Column("charging_power_kw", sa.Float(), nullable=True),
        sa.Column("charging_power_limit_kw", sa.Float(), nullable=True),
        sa.Column("estimated_charge_complete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("departure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_state", sa.String(length=32), nullable=False, server_default="DISCONNECTED"),
        sa.Column("data_quality", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_vehicle_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_provider_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vehicle_id"),
    )

    op.create_table(
        "vehicle_state_history",
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state_of_charge_percent", sa.Float(), nullable=True),
        sa.Column("target_soc_percent", sa.Float(), nullable=True),
        sa.Column("electric_range_km", sa.Float(), nullable=True),
        sa.Column("is_plugged_in", sa.Boolean(), nullable=True),
        sa.Column("is_charging", sa.Boolean(), nullable=True),
        sa.Column("charging_power_kw", sa.Float(), nullable=True),
        sa.Column("connection_state", sa.String(length=32), nullable=False, server_default="DISCONNECTED"),
        sa.Column("data_quality", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vehicle_id", "recorded_at"),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql" and os.environ.get("ENABLE_TIMESCALEDB", "false").lower() in (
        "1",
        "true",
        "yes",
    ):
        op.execute(
            "SELECT create_hypertable('vehicle_state_history', 'recorded_at', "
            "if_not_exists => TRUE, migrate_data => TRUE)"
        )


def downgrade() -> None:
    op.drop_table("vehicle_state_history")
    op.drop_table("vehicle_state_latest")
    op.drop_table("vehicle_capabilities")
    op.drop_table("vehicles")
    op.drop_index("ix_vehicle_provider_connections_site_id", table_name="vehicle_provider_connections")
    op.drop_table("vehicle_provider_connections")
