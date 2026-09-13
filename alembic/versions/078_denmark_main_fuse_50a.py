"""078 — correct Denmark main fuse rating (50 A)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "078_denmark_main_fuse_50a"
down_revision = "077_user_site_prefs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE sites SET main_fuse_a = 50 "
            "WHERE slug = 'summer-house-denmark' "
            "AND (main_fuse_a IS NULL OR main_fuse_a <= 25)"
        )
    )


def downgrade() -> None:
    pass
