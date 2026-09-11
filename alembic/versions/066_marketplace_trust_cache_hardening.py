"""066 — marketplace trust cache hardening columns (Step 5C.1.5)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "066_marketplace_trust_cache_hardening"
down_revision = "065_marketplace_trust_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketplace_trust_cache",
        sa.Column("revocation_generation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "marketplace_trust_cache",
        sa.Column("revocation_content_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "marketplace_trust_cache",
        sa.Column("catalog_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "marketplace_trust_cache",
        sa.Column("revocation_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketplace_trust_cache", "revocation_updated_at")
    op.drop_column("marketplace_trust_cache", "catalog_updated_at")
    op.drop_column("marketplace_trust_cache", "revocation_content_hash")
    op.drop_column("marketplace_trust_cache", "revocation_generation")
