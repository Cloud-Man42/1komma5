"""Remove Heartbeat EV profile write/sync columns."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "031_drop_heartbeat_ev_sync"
down_revision = "030_heartbeat_ev_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("ev_chargers", "heartbeat_sync_error")
    op.drop_column("ev_chargers", "heartbeat_remote_updated_at")
    op.drop_column("ev_chargers", "heartbeat_last_pulled_at")
    op.drop_column("ev_chargers", "heartbeat_last_pushed_at")
    op.drop_column("ev_chargers", "heartbeat_sync_enabled")
    op.drop_column("heartbeat_settings", "heartbeat_write_enabled")


def downgrade() -> None:
    op.add_column(
        "heartbeat_settings",
        sa.Column("heartbeat_write_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("heartbeat_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("heartbeat_last_pushed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("heartbeat_last_pulled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("heartbeat_remote_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("heartbeat_sync_error", sa.String(length=512), nullable=True),
    )
