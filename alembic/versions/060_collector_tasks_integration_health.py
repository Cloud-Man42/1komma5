"""Collector task runs and integration health tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "060_collector_tasks_integration_health"
down_revision = "059_financial_daily"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collector_task_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_name", sa.String(length=64), nullable=False),
        sa.Column("lane", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_class", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_collector_task_runs_started_at", "collector_task_runs", ["started_at"])
    op.create_index("ix_collector_task_runs_lane", "collector_task_runs", ["lane"])

    op.create_table(
        "integration_health",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stale_seconds", sa.Float(), nullable=True),
        sa.Column("circuit_breaker_state", sa.String(length=16), nullable=True),
        sa.Column("last_error_class", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("site_id", "provider"),
    )


def downgrade() -> None:
    op.drop_table("integration_health")
    op.drop_index("ix_collector_task_runs_lane", table_name="collector_task_runs")
    op.drop_index("ix_collector_task_runs_started_at", table_name="collector_task_runs")
    op.drop_table("collector_task_runs")
