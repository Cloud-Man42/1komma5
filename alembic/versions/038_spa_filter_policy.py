"""Spa filter policy — fixed 4×2 h cycle optimization."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "038_spa_filter_policy"
down_revision = "037_spa_cleaning_windows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "spa_control_config",
        sa.Column("filter_cycles_per_day", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "spa_control_config",
        sa.Column("filter_duration_minutes", sa.Integer(), nullable=False, server_default="120"),
    )
    op.add_column(
        "spa_control_config",
        sa.Column("minimum_cycle_separation_minutes", sa.Integer(), nullable=False, server_default="60"),
    )
    op.add_column(
        "spa_control_config",
        sa.Column("filter_optimization_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "spa_control_config",
        sa.Column("last_known_safe_filter_schedule_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("spa_control_config", "last_known_safe_filter_schedule_json")
    op.drop_column("spa_control_config", "filter_optimization_enabled")
    op.drop_column("spa_control_config", "minimum_cycle_separation_minutes")
    op.drop_column("spa_control_config", "filter_duration_minutes")
    op.drop_column("spa_control_config", "filter_cycles_per_day")
