"""Add indexes for common query filters."""

from __future__ import annotations

from alembic import op

revision = "042_query_performance_indexes"
down_revision = "041_market_price_eur_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_ev_charging_sessions_status", "ev_charging_sessions", ["status"])
    op.create_index(
        "ix_flexible_load_plan_site_load_created",
        "flexible_load_plan",
        ["site_id", "load_id", "created_at"],
    )
    op.create_index(
        "ix_heartbeat_discovery_runs_site_started",
        "heartbeat_discovery_runs",
        ["site_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_heartbeat_discovery_runs_site_started", table_name="heartbeat_discovery_runs")
    op.drop_index("ix_flexible_load_plan_site_load_created", table_name="flexible_load_plan")
    op.drop_index("ix_ev_charging_sessions_status", table_name="ev_charging_sessions")
