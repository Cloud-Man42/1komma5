"""Admin audit log for configuration mutations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "061_admin_audit_log"
down_revision = "060_collector_tasks_integration_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("site_slug", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=True),
    )
    op.create_index("ix_admin_audit_log_recorded_at", "admin_audit_log", ["recorded_at"])
    op.create_index("ix_admin_audit_log_site_slug", "admin_audit_log", ["site_slug"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_log_site_slug", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_recorded_at", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
