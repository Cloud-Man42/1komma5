"""Apple device registration table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "033_apple_devices"
down_revision = "031_drop_heartbeat_ev_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apple_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_label", sa.String(length=128), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=False),
        sa.Column("device_type", sa.String(length=64), nullable=False, server_default="iphone"),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.String(length=256), nullable=False, server_default="widget.read"),
        sa.Column("default_site_slug", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_prefix"),
    )
    op.create_index("ix_apple_devices_token_prefix", "apple_devices", ["token_prefix"])


def downgrade() -> None:
    op.drop_index("ix_apple_devices_token_prefix", table_name="apple_devices")
    op.drop_table("apple_devices")
