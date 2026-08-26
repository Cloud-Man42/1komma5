"""Spa smart control tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "034_spa_smart_control"
down_revision = "033_apple_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spa_control_config",
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("smart_control_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("strategy", sa.String(length=32), nullable=False, server_default="SMART"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("shadow_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("shadow_mode_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("min_cleaning_hours_per_day", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("allowed_window_start", sa.String(length=8), nullable=False, server_default="07:00"),
        sa.Column("allowed_window_end", sa.String(length=8), nullable=False, server_default="22:00"),
        sa.Column("prefer_solar", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_battery", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_battery_soc_pct", sa.Float(), nullable=False, server_default="40.0"),
        sa.Column("min_run_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("min_stop_minutes", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("max_starts_per_day", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("safety_floor_frequency_per_day", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("safety_floor_duration_hours", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("smart_preheat_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("normal_temperature_c", sa.Float(), nullable=False, server_default="38.0"),
        sa.Column("max_preheat_temperature_c", sa.Float(), nullable=False, server_default="39.0"),
        sa.Column("min_comfort_temperature_c", sa.Float(), nullable=False, server_default="37.0"),
        sa.Column("load_priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("fixed_schedule_start", sa.String(length=8), nullable=True),
        sa.Column("fixed_schedule_end", sa.String(length=8), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consumer_id"),
    )
    op.create_table(
        "spa_energy_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stop_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runtime_seconds", sa.Float(), nullable=True),
        sa.Column("estimated_kwh", sa.Float(), nullable=True),
        sa.Column("actual_kwh", sa.Float(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("solar_share", sa.Float(), nullable=True),
        sa.Column("battery_share", sa.Float(), nullable=True),
        sa.Column("grid_share", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("reason_sv", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("strategy", sa.String(length=32), nullable=False, server_default="SMART"),
        sa.Column("decision_score", sa.Float(), nullable=True),
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("shadow", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spa_energy_event_timestamp", "spa_energy_event", ["timestamp"])
    op.create_index("ix_spa_energy_event_consumer_id", "spa_energy_event", ["consumer_id"])
    op.create_table(
        "flexible_load_plan",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("consumer_id", sa.Integer(), nullable=True),
        sa.Column("load_id", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("reason_sv", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("explanation_sv", sa.Text(), nullable=False, server_default=""),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_energy_kwh", sa.Float(), nullable=True),
        sa.Column("expected_cost_sek", sa.Float(), nullable=True),
        sa.Column("baseline_cost_sek", sa.Float(), nullable=True),
        sa.Column("savings_sek", sa.Float(), nullable=True),
        sa.Column("expected_energy_source", sa.String(length=16), nullable=True),
        sa.Column("fallback_from_solar_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flexible_load_plan_site_id", "flexible_load_plan", ["site_id"])
    op.create_table(
        "flexible_load_plan_block",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("solar_forecast_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("house_load_forecast_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("available_surplus_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("marginal_cost_sek_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expected_energy_source", sa.String(length=16), nullable=False, server_default="GRID"),
        sa.Column("price_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["plan_id"], ["flexible_load_plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flexible_load_plan_block_plan_id", "flexible_load_plan_block", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_flexible_load_plan_block_plan_id", table_name="flexible_load_plan_block")
    op.drop_table("flexible_load_plan_block")
    op.drop_index("ix_flexible_load_plan_site_id", table_name="flexible_load_plan")
    op.drop_table("flexible_load_plan")
    op.drop_index("ix_spa_energy_event_consumer_id", table_name="spa_energy_event")
    op.drop_index("ix_spa_energy_event_timestamp", table_name="spa_energy_event")
    op.drop_table("spa_energy_event")
    op.drop_table("spa_control_config")
