"""065 — marketplace trust metadata cache (Step 5C.1)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "065_marketplace_trust_cache"
down_revision = "064_module_publisher_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_trust_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cache_key", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cache_state", sa.String(length=32), nullable=False, server_default="uninitialized"),
        sa.Column("revocation_state", sa.String(length=32), nullable=False, server_default="unavailable"),
        sa.Column("cache_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("root_version", sa.Integer(), nullable=True),
        sa.Column("timestamp_version", sa.Integer(), nullable=True),
        sa.Column("snapshot_version", sa.Integer(), nullable=True),
        sa.Column("targets_version", sa.Integer(), nullable=True),
        sa.Column("catalog_json", sa.Text(), nullable=True),
        sa.Column("revocations_json", sa.Text(), nullable=True),
        sa.Column("metadata_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sync_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pinned_root_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_marketplace_trust_cache_cache_key", "marketplace_trust_cache", ["cache_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_marketplace_trust_cache_cache_key", table_name="marketplace_trust_cache")
    op.drop_table("marketplace_trust_cache")
