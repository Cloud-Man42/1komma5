"""EV energy accounting tables and extended energy readings."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "018_ev_energy_accounting"
down_revision = "017_drop_bridge_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ev_charging_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("charger_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("meter_start_kwh", sa.Float(), nullable=True),
        sa.Column("meter_stop_kwh", sa.Float(), nullable=True),
        sa.Column("total_energy_kwh", sa.Float(), nullable=True),
        sa.Column("solar_direct_kwh", sa.Float(), nullable=True),
        sa.Column("solar_battery_kwh", sa.Float(), nullable=True),
        sa.Column("grid_battery_kwh", sa.Float(), nullable=True),
        sa.Column("grid_direct_kwh", sa.Float(), nullable=True),
        sa.Column("actual_cost_sek", sa.Float(), nullable=True),
        sa.Column("reference_cost_sek", sa.Float(), nullable=True),
        sa.Column("savings_sek", sa.Float(), nullable=True),
        sa.Column("smart_charging_savings_sek", sa.Float(), nullable=True),
        sa.Column("solar_contribution_sek", sa.Float(), nullable=True),
        sa.Column("renewable_share_pct", sa.Float(), nullable=True),
        sa.Column("grid_share_pct", sa.Float(), nullable=True),
        sa.Column("energy_quality", sa.String(length=16), nullable=True),
        sa.Column("cost_quality", sa.String(length=16), nullable=True),
        sa.Column("attribution_quality", sa.String(length=16), nullable=True),
        sa.Column("savings_baseline", sa.String(length=32), nullable=False, server_default="IMMEDIATE_GRID_CHARGING"),
        sa.Column("calculation_version", sa.String(length=32), nullable=False, server_default="ev-energy-v1"),
        sa.Column("reconciliation_delta_kwh", sa.Float(), nullable=True),
        sa.Column("reconciliation_note", sa.String(length=128), nullable=True),
        sa.Column("chargeamps_session_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ev_charging_sessions_charger_started", "ev_charging_sessions", ["charger_id", "started_at"])

    op.create_table(
        "ev_charging_intervals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["session_id"], ["ev_charging_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ev_charging_intervals_session_start", "ev_charging_intervals", ["session_id", "start_time"])
    op.create_index("ix_ev_charging_intervals_charger_start", "ev_charging_intervals", ["charger_id", "start_time"])

    op.create_table(
        "battery_energy_ledger",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("solar_energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_energy_cost_sek", sa.Float(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("site_id", "recorded_at"),
    )

    op.add_column("energy_readings", sa.Column("ev_power_w", sa.Float(), nullable=True))
    op.add_column("energy_readings", sa.Column("battery_charge_w", sa.Float(), nullable=True))
    op.add_column("energy_readings", sa.Column("battery_discharge_w", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("energy_readings", "battery_discharge_w")
    op.drop_column("energy_readings", "battery_charge_w")
    op.drop_column("energy_readings", "ev_power_w")
    op.drop_table("battery_energy_ledger")
    op.drop_index("ix_ev_charging_intervals_charger_start", table_name="ev_charging_intervals")
    op.drop_index("ix_ev_charging_intervals_session_start", table_name="ev_charging_intervals")
    op.drop_table("ev_charging_intervals")
    op.drop_index("ix_ev_charging_sessions_charger_started", table_name="ev_charging_sessions")
    op.drop_table("ev_charging_sessions")
