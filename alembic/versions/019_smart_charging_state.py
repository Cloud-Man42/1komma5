"""Smart charging persistent state and stability configuration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "019_smart_charging_state"
down_revision = "018_ev_energy_accounting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ev_chargers", sa.Column("smart_charging_state", sa.String(length=32), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_requested_current_a", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_configured_current_a", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_actual_charging_current_a", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_actual_power_w", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("externally_limited", sa.Boolean(), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_stop_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "ev_chargers",
        sa.Column("start_delay_seconds", sa.Integer(), nullable=False, server_default="120"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("stop_delay_seconds", sa.Integer(), nullable=False, server_default="300"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("minimum_run_time_seconds", sa.Integer(), nullable=False, server_default="300"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("minimum_off_time_seconds", sa.Integer(), nullable=False, server_default="300"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("temporary_grid_import_allowance_w", sa.Float(), nullable=False, server_default="800"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("temporary_grid_import_seconds", sa.Integer(), nullable=False, server_default="180"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("grid_deadband_w", sa.Float(), nullable=False, server_default="300"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("minimum_current_change_interval_seconds", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("max_current_increase_per_step_a", sa.Float(), nullable=False, server_default="1"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("max_current_decrease_per_step_a", sa.Float(), nullable=False, server_default="2"),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("max_automatic_starts_per_hour", sa.Integer(), nullable=False, server_default="4"),
    )


def downgrade() -> None:
    op.drop_column("ev_chargers", "max_automatic_starts_per_hour")
    op.drop_column("ev_chargers", "max_current_decrease_per_step_a")
    op.drop_column("ev_chargers", "max_current_increase_per_step_a")
    op.drop_column("ev_chargers", "minimum_current_change_interval_seconds")
    op.drop_column("ev_chargers", "grid_deadband_w")
    op.drop_column("ev_chargers", "temporary_grid_import_seconds")
    op.drop_column("ev_chargers", "temporary_grid_import_allowance_w")
    op.drop_column("ev_chargers", "minimum_off_time_seconds")
    op.drop_column("ev_chargers", "minimum_run_time_seconds")
    op.drop_column("ev_chargers", "stop_delay_seconds")
    op.drop_column("ev_chargers", "start_delay_seconds")
    op.drop_column("ev_chargers", "last_stop_at")
    op.drop_column("ev_chargers", "last_start_at")
    op.drop_column("ev_chargers", "externally_limited")
    op.drop_column("ev_chargers", "last_actual_power_w")
    op.drop_column("ev_chargers", "last_actual_charging_current_a")
    op.drop_column("ev_chargers", "last_configured_current_a")
    op.drop_column("ev_chargers", "last_requested_current_a")
    op.drop_column("ev_chargers", "smart_charging_state")
