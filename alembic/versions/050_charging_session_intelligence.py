"""Charging Session Intelligence tables and vehicle session extensions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "050_charging_session_intelligence"
down_revision = "049_mercedes_health_diagnostics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charging_locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("expected_operator", sa.String(length=128), nullable=True),
        sa.Column("expected_network", sa.String(length=128), nullable=True),
        sa.Column("expected_charging_type", sa.String(length=16), nullable=True),
        sa.Column("charger_id", sa.Integer(), sa.ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("price_model", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
        sa.Column("price_value", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_charging_locations_site_id", "charging_locations", ["site_id"])

    op.create_table(
        "charging_location_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("location_name", sa.String(length=128), nullable=False),
        sa.Column("charger_operator", sa.String(length=128), nullable=True),
        sa.Column("charging_type", sa.String(length=16), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "vehicle_charge_state_transitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("vehicle_charge_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(length=32), nullable=True),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger", sa.String(length=64), nullable=False, server_default=""),
    )

    op.create_table(
        "vehicle_charge_session_revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("vehicle_charge_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("previous_value", sa.String(length=256), nullable=True),
        sa.Column("new_value", sa.String(length=256), nullable=True),
        sa.Column("revision_reason", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("revised_at", sa.DateTime(timezone=True), nullable=False),
    )

    with op.batch_alter_table("vehicle_charge_sessions") as batch:
        batch.alter_column("charger_id", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("ev_charging_session_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("location_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("location_name", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("charger_operator", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("charger_network", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("charging_type", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("connector_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("home_charging", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("energy_source", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("estimated_energy_kwh", sa.Float(), nullable=True))
        batch.add_column(sa.Column("charging_power_avg_kw", sa.Float(), nullable=True))
        batch.add_column(sa.Column("charging_power_max_kw", sa.Float(), nullable=True))
        batch.add_column(sa.Column("charging_cost_sek", sa.Float(), nullable=True))
        batch.add_column(sa.Column("cost_source", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("detection_confidence", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("identification_method", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("vehicle_data_quality", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("charging_state", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("vehicle_charge_sessions") as batch:
        for col in (
            "charging_state",
            "vehicle_data_quality",
            "identification_method",
            "detection_confidence",
            "cost_source",
            "charging_cost_sek",
            "charging_power_max_kw",
            "charging_power_avg_kw",
            "estimated_energy_kwh",
            "energy_source",
            "home_charging",
            "connector_type",
            "charging_type",
            "charger_network",
            "charger_operator",
            "location_name",
            "location_id",
            "longitude",
            "latitude",
            "ev_charging_session_id",
        ):
            batch.drop_column(col)
        batch.alter_column("charger_id", existing_type=sa.Integer(), nullable=False)

    op.drop_table("vehicle_charge_session_revisions")
    op.drop_table("vehicle_charge_state_transitions")
    op.drop_table("charging_location_observations")
    op.drop_index("ix_charging_locations_site_id", table_name="charging_locations")
    op.drop_table("charging_locations")
