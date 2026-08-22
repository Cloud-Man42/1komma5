"""Energy balance diagnostics tables and Virtual EVSE fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "022_energy_balance_diagnostics"
down_revision = "021_solar_forecast_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_energy_config",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("load_includes_ev_charger", sa.Boolean(), nullable=True),
        sa.Column(
            "inverter_display_name",
            sa.String(length=128),
            nullable=False,
            server_default="Sungrow Hybrid Inverter SH10",
        ),
        sa.Column(
            "physical_ev_charger_label",
            sa.String(length=128),
            nullable=False,
            server_default="Charge Amps Halo",
        ),
        sa.Column(
            "ev_vehicle_label",
            sa.String(length=128),
            nullable=False,
            server_default="Mercedes EQE 500",
        ),
    )

    op.create_table(
        "energy_balance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charger_id", sa.Integer(), sa.ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("flags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_energy_balance_snapshots_site_id", "energy_balance_snapshots", ["site_id"])
    op.create_index("ix_energy_balance_snapshots_charger_id", "energy_balance_snapshots", ["charger_id"])
    op.create_index("ix_energy_balance_snapshots_recorded_at", "energy_balance_snapshots", ["recorded_at"])

    op.add_column(
        "ev_chargers",
        sa.Column("virtual_evse_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("ev_chargers", sa.Column("semp_device_id", sa.String(length=128), nullable=True))
    op.add_column("ev_chargers", sa.Column("semp_endpoint_registered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("ev_chargers", "semp_endpoint_registered_at")
    op.drop_column("ev_chargers", "semp_device_id")
    op.drop_column("ev_chargers", "virtual_evse_enabled")
    op.drop_index("ix_energy_balance_snapshots_recorded_at", table_name="energy_balance_snapshots")
    op.drop_index("ix_energy_balance_snapshots_charger_id", table_name="energy_balance_snapshots")
    op.drop_index("ix_energy_balance_snapshots_site_id", table_name="energy_balance_snapshots")
    op.drop_table("energy_balance_snapshots")
    op.drop_table("site_energy_config")
