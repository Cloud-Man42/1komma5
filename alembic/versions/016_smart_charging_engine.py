"""Smart charging configuration and runtime status fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "016_smart_charging_engine"
down_revision = "015_tibber_history_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("main_fuse_a", sa.Float(), nullable=True))
    op.add_column("sites", sa.Column("safety_margin_a", sa.Float(), nullable=False, server_default="2.0"))

    op.add_column("ev_chargers", sa.Column("required_energy_kwh", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ev_chargers", sa.Column("solar_start_threshold_w", sa.Float(), nullable=False, server_default="1500"))
    op.add_column("ev_chargers", sa.Column("solar_stop_threshold_w", sa.Float(), nullable=False, server_default="800"))
    op.add_column("ev_chargers", sa.Column("solar_start_delay_seconds", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("ev_chargers", sa.Column("solar_stop_delay_seconds", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("ev_chargers", sa.Column("last_charging_action", sa.String(length=32), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_charging_reason", sa.String(length=64), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_charger_error_code", sa.String(length=32), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_halo_connected", sa.Boolean(), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_vehicle_connected", sa.Boolean(), nullable=True))

    op.execute("UPDATE ev_chargers SET control_source = 'chargeamp' WHERE control_source = 'heartbeat'")
    # Batch mode so SQLite, which cannot ALTER COLUMN, rebuilds the table instead.
    with op.batch_alter_table("ev_chargers") as batch:
        batch.alter_column(
            "control_source",
            existing_type=sa.String(length=16),
            existing_nullable=False,
            server_default="chargeamp",
        )


def downgrade() -> None:
    with op.batch_alter_table("ev_chargers") as batch:
        batch.alter_column(
            "control_source",
            existing_type=sa.String(length=16),
            existing_nullable=False,
            server_default="heartbeat",
        )
    op.drop_column("ev_chargers", "last_vehicle_connected")
    op.drop_column("ev_chargers", "last_halo_connected")
    op.drop_column("ev_chargers", "last_charger_error_code")
    op.drop_column("ev_chargers", "last_charging_reason")
    op.drop_column("ev_chargers", "last_charging_action")
    op.drop_column("ev_chargers", "solar_stop_delay_seconds")
    op.drop_column("ev_chargers", "solar_start_delay_seconds")
    op.drop_column("ev_chargers", "solar_stop_threshold_w")
    op.drop_column("ev_chargers", "solar_start_threshold_w")
    op.drop_column("ev_chargers", "deadline_at")
    op.drop_column("ev_chargers", "required_energy_kwh")
    op.drop_column("sites", "safety_margin_a")
    op.drop_column("sites", "main_fuse_a")
