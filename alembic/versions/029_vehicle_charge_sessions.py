"""Vehicle charge sessions and energy attribution."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "029_vehicle_charge_sessions"
down_revision = "028_vehicle_halo_correlation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_charge_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("charger_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("charging_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("charging_stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_soc", sa.Float(), nullable=True),
        sa.Column("end_soc", sa.Float(), nullable=True),
        sa.Column("target_soc", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("meter_start_kwh", sa.Float(), nullable=True),
        sa.Column("meter_stop_kwh", sa.Float(), nullable=True),
        sa.Column("halo_energy_kwh", sa.Float(), nullable=True),
        sa.Column("estimated_battery_energy_delta_kwh", sa.Float(), nullable=True),
        sa.Column("solar_direct_kwh", sa.Float(), nullable=True),
        sa.Column("solar_battery_kwh", sa.Float(), nullable=True),
        sa.Column("grid_battery_kwh", sa.Float(), nullable=True),
        sa.Column("grid_direct_kwh", sa.Float(), nullable=True),
        sa.Column("actual_cost_sek", sa.Float(), nullable=True),
        sa.Column("reference_cost_sek", sa.Float(), nullable=True),
        sa.Column("savings_sek", sa.Float(), nullable=True),
        sa.Column("renewable_share_pct", sa.Float(), nullable=True),
        sa.Column("grid_share_pct", sa.Float(), nullable=True),
        sa.Column("identification_confidence", sa.Float(), nullable=True),
        sa.Column("energy_quality", sa.String(length=16), nullable=True),
        sa.Column("cost_quality", sa.String(length=16), nullable=True),
        sa.Column("attribution_quality", sa.String(length=16), nullable=True),
        sa.Column("savings_baseline", sa.String(length=32), nullable=False, server_default="IMMEDIATE_GRID_CHARGING"),
        sa.Column("calculation_version", sa.String(length=32), nullable=False, server_default="vehicle-charge-v1"),
        sa.Column("reconciliation_delta_kwh", sa.Float(), nullable=True),
        sa.Column("reconciliation_note", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_charge_sessions_vehicle_id", "vehicle_charge_sessions", ["vehicle_id"])
    op.create_index("ix_vehicle_charge_sessions_charger_id", "vehicle_charge_sessions", ["charger_id"])
    op.create_index("ix_vehicle_charge_sessions_site_id", "vehicle_charge_sessions", ["site_id"])

    op.create_table(
        "vehicle_charging_intervals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("charger_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("charged_energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_charging_power_w", sa.Float(), nullable=True),
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
        sa.Column("actual_cost_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reference_cost_sek", sa.Float(), nullable=True),
        sa.Column("savings_sek", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("data_quality", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["vehicle_charge_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_charging_intervals_session_id", "vehicle_charging_intervals", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_vehicle_charging_intervals_session_id", table_name="vehicle_charging_intervals")
    op.drop_table("vehicle_charging_intervals")
    op.drop_index("ix_vehicle_charge_sessions_site_id", table_name="vehicle_charge_sessions")
    op.drop_index("ix_vehicle_charge_sessions_charger_id", table_name="vehicle_charge_sessions")
    op.drop_index("ix_vehicle_charge_sessions_vehicle_id", table_name="vehicle_charge_sessions")
    op.drop_table("vehicle_charge_sessions")
