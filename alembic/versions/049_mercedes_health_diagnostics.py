"""Mercedes integration health and API event persistence columns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "049_mercedes_health_diagnostics"
down_revision = "048_vehicle_attribute_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vehicle_provider_connections") as batch:
        batch.add_column(sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_token_refresh_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_error_code", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("last_latency_ms", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("current_polling_interval_seconds", sa.Integer(), nullable=True))

    with op.batch_alter_table("vehicle_state_latest") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("soc_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("charging_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("range_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("usable_battery_kwh", sa.Float(), nullable=True))

    with op.batch_alter_table("vehicles") as batch:
        batch.add_column(sa.Column("usable_battery_kwh", sa.Float(), nullable=True))

    op.create_table(
        "vehicle_api_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("vehicle_provider_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(length=512), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False, server_default="GET"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vehicle_api_events_connection_id", "vehicle_api_events", ["connection_id"])


def downgrade() -> None:
    op.drop_index("ix_vehicle_api_events_connection_id", table_name="vehicle_api_events")
    op.drop_table("vehicle_api_events")
    with op.batch_alter_table("vehicles") as batch:
        batch.drop_column("usable_battery_kwh")
    with op.batch_alter_table("vehicle_state_latest") as batch:
        batch.drop_column("usable_battery_kwh")
        batch.drop_column("range_updated_at")
        batch.drop_column("charging_updated_at")
        batch.drop_column("soc_updated_at")
        batch.drop_column("location_updated_at")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
    with op.batch_alter_table("vehicle_provider_connections") as batch:
        batch.drop_column("current_polling_interval_seconds")
        batch.drop_column("last_latency_ms")
        batch.drop_column("last_error_code")
        batch.drop_column("consecutive_failures")
        batch.drop_column("last_token_refresh_at")
        batch.drop_column("last_failure_at")
        batch.drop_column("last_success_at")
