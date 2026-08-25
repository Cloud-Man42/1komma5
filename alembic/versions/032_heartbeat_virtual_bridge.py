"""Remove Heartbeat EV profile write/sync columns."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "032_heartbeat_virtual_bridge"
down_revision = "031_drop_heartbeat_ev_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "heartbeat_discovery_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="COMPLETED"),
        sa.Column("system_id", sa.String(length=128), nullable=True),
        sa.Column("conclusion_class", sa.String(length=8), nullable=True),
        sa.Column("bridge_lifecycle", sa.String(length=64), nullable=True),
        sa.Column("resolved_ev_id", sa.String(length=128), nullable=True),
        sa.Column("confidence_pct", sa.Float(), nullable=True),
        sa.Column("report_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("report_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_discovery_runs_site_id", "heartbeat_discovery_runs", ["site_id"])

    op.create_table(
        "heartbeat_api_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observation_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("schema_fingerprint", sa.String(length=32), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["heartbeat_discovery_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_api_observations_run_id", "heartbeat_api_observations", ["run_id"])

    op.create_table(
        "heartbeat_ev_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("heartbeat_ev_id", sa.String(length=128), nullable=False),
        sa.Column("heartbeat_ev_name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("physical_charger_id", sa.Integer(), nullable=True),
        sa.Column("vehicle_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="heartbeat"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_discovery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["physical_charger_id"], ["ev_chargers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_ev_mappings_site_id", "heartbeat_ev_mappings", ["site_id"])

    op.create_table(
        "heartbeat_bridge_settings",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("discovery_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("write_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("virtual_bridge_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("physical_control_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("soc_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("replay_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("simulation_mode", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("confidence_threshold_pct", sa.Float(), nullable=False, server_default="90"),
        sa.Column("battery_priority_mode", sa.String(length=32), nullable=False, server_default="BATTERY_FIRST"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("site_id"),
    )

    op.create_table(
        "heartbeat_write_tests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("heartbeat_ev_id", sa.String(length=128), nullable=False),
        sa.Column("classification", sa.String(length=64), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_write_tests_site_id", "heartbeat_write_tests", ["site_id"])

    op.create_table(
        "virtual_charger_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("charger_id", sa.Integer(), nullable=True),
        sa.Column("heartbeat_ev_id", sa.String(length=128), nullable=True),
        sa.Column("bridge_state", sa.String(length=64), nullable=False),
        sa.Column("heartbeat_mode", sa.String(length=32), nullable=True),
        sa.Column("ai_decision", sa.String(length=128), nullable=True),
        sa.Column("decision_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("reason", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_virtual_charger_decisions_site_id", "virtual_charger_decisions", ["site_id"])
    op.create_index("ix_virtual_charger_decisions_recorded_at", "virtual_charger_decisions", ["recorded_at"])

    op.create_table(
        "virtual_charger_commands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("charger_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("current_a", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_virtual_charger_commands_site_id", "virtual_charger_commands", ["site_id"])

    op.create_table(
        "virtual_charger_replay_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("report_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("report_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_virtual_charger_replay_runs_site_id", "virtual_charger_replay_runs", ["site_id"])


def downgrade() -> None:
    op.drop_table("virtual_charger_replay_runs")
    op.drop_table("virtual_charger_commands")
    op.drop_table("virtual_charger_decisions")
    op.drop_table("heartbeat_write_tests")
    op.drop_table("heartbeat_bridge_settings")
    op.drop_table("heartbeat_ev_mappings")
    op.drop_table("heartbeat_api_observations")
    op.drop_table("heartbeat_discovery_runs")
