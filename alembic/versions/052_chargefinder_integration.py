"""Migration 052: Replace NOBIL integration with ChargeFinder (legacy migration – NOBIL integration removed)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "052_chargefinder_integration"
down_revision = "051_nobil_charging_stations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "nobil_integration_status" in inspector.get_table_names():
        op.drop_table("nobil_integration_status")

    if "chargefinder_integration_status" not in inspector.get_table_names():
        op.create_table(
            "chargefinder_integration_status",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_lookup_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_latency_ms", sa.Integer(), nullable=True),
            sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.String(length=512), nullable=True),
            sa.Column("cache_hits", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cache_misses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parser_failures", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("lookup_mode", sa.String(length=16), nullable=True),
            sa.Column("browser_status", sa.String(length=64), nullable=True),
            sa.Column("parsing_version", sa.String(length=16), nullable=False, server_default="1"),
        )

    charging_cols = {c["name"] for c in inspector.get_columns("charging_station")}
    if "external_station_url" not in charging_cols:
        with op.batch_alter_table("charging_station") as batch:
            batch.add_column(sa.Column("external_station_url", sa.String(length=512), nullable=True))
            batch.add_column(sa.Column("network_name", sa.String(length=128), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE charging_station
            SET provider = 'CHARGEFINDER'
            WHERE provider = 'NOBIL'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE vehicle_charge_sessions
            SET station_provider = 'CHARGEFINDER'
            WHERE station_provider = 'NOBIL'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chargefinder_integration_status" in inspector.get_table_names():
        op.drop_table("chargefinder_integration_status")
    if "nobil_integration_status" not in inspector.get_table_names():
        op.create_table(
            "nobil_integration_status",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_latency_ms", sa.Integer(), nullable=True),
            sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.String(length=512), nullable=True),
            sa.Column("cache_hits", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cache_misses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("requests_last_hour", sa.Integer(), nullable=False, server_default="0"),
        )
    charging_cols = {c["name"] for c in inspector.get_columns("charging_station")}
    if "external_station_url" in charging_cols:
        with op.batch_alter_table("charging_station") as batch:
            batch.drop_column("network_name")
            batch.drop_column("external_station_url")
