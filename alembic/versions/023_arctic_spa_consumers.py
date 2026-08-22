"""Arctic Spa energy consumer tables."""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "023_arctic_spa_consumers"
down_revision = "022_energy_balance_diagnostics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "energy_consumers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("consumer_type", sa.String(length=32), nullable=False, server_default="SPA"),
        sa.Column("name", sa.String(length=128), nullable=False, server_default="Arctic Spa"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Europe/Stockholm"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "consumer_type", name="uq_energy_consumers_site_type"),
    )

    op.create_table(
        "spa_device_config",
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("integration_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("api_base_url", sa.String(length=255), nullable=False, server_default="https://api.myarcticspa.com"),
        sa.Column("api_key", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("external_spa_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("energy_collection_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cost_calculation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("power_profiles_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("last_status_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("last_status_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consumer_id"),
    )

    op.create_table(
        "spa_poll_state",
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.String(length=512), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sample_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("polling_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consumer_id"),
    )

    op.create_table(
        "consumer_samples",
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("power_w", sa.Float(), nullable=True),
        sa.Column("energy_delta_wh", sa.Float(), nullable=True),
        sa.Column("water_temperature_c", sa.Float(), nullable=True),
        sa.Column("set_temperature_c", sa.Float(), nullable=True),
        sa.Column("heater_active", sa.Boolean(), nullable=True),
        sa.Column("pump_states_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("filter_status", sa.String(length=32), nullable=True),
        sa.Column("spa_connected", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="ARCTIC_SPA_REST"),
        sa.Column("quality", sa.String(length=16), nullable=False, server_default="CALCULATED"),
        sa.Column("component_breakdown_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consumer_id", "recorded_at"),
    )
    op.create_index("ix_consumer_samples_consumer_recorded", "consumer_samples", ["consumer_id", "recorded_at"])

    op.create_table(
        "consumer_intervals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_power_w", sa.Float(), nullable=True),
        sa.Column("pv_production_kwh", sa.Float(), nullable=True),
        sa.Column("house_consumption_kwh", sa.Float(), nullable=True),
        sa.Column("grid_import_kwh", sa.Float(), nullable=True),
        sa.Column("grid_export_kwh", sa.Float(), nullable=True),
        sa.Column("battery_charge_kwh", sa.Float(), nullable=True),
        sa.Column("battery_discharge_kwh", sa.Float(), nullable=True),
        sa.Column("electricity_price_sek_kwh", sa.Float(), nullable=True),
        sa.Column("solar_direct_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("solar_battery_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_battery_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_direct_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unknown_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_cost_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reference_cost_sek", sa.Float(), nullable=True),
        sa.Column("savings_sek", sa.Float(), nullable=True),
        sa.Column("heater_runtime_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pump_runtime_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("data_quality", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumer_intervals_consumer_start", "consumer_intervals", ["consumer_id", "start_time"])

    op.create_table(
        "consumer_aggregates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("granularity", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("solar_direct_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("solar_battery_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_battery_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_direct_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unknown_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_cost_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reference_cost_sek", sa.Float(), nullable=True),
        sa.Column("savings_sek", sa.Float(), nullable=True),
        sa.Column("max_power_w", sa.Float(), nullable=True),
        sa.Column("avg_power_w", sa.Float(), nullable=True),
        sa.Column("heater_runtime_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pump_runtime_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("measured_pct", sa.Float(), nullable=True),
        sa.Column("calculated_pct", sa.Float(), nullable=True),
        sa.Column("estimated_pct", sa.Float(), nullable=True),
        sa.Column("missing_pct", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumer_id", "granularity", "period_start", name="uq_consumer_aggregates_period"),
    )
    op.create_index("ix_consumer_aggregates_consumer_granularity", "consumer_aggregates", ["consumer_id", "granularity", "period_start"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql" and os.environ.get("ENABLE_TIMESCALEDB", "false").lower() in ("1", "true", "yes"):
        op.execute(
            "SELECT create_hypertable('consumer_samples', 'recorded_at', "
            "if_not_exists => TRUE, migrate_data => TRUE)"
        )


def downgrade() -> None:
    op.drop_index("ix_consumer_aggregates_consumer_granularity", table_name="consumer_aggregates")
    op.drop_table("consumer_aggregates")
    op.drop_index("ix_consumer_intervals_consumer_start", table_name="consumer_intervals")
    op.drop_table("consumer_intervals")
    op.drop_index("ix_consumer_samples_consumer_recorded", table_name="consumer_samples")
    op.drop_table("consumer_samples")
    op.drop_table("spa_poll_state")
    op.drop_table("spa_device_config")
    op.drop_table("energy_consumers")
