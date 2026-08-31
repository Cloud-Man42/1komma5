"""Deduplicate heartbeat_ev_mappings and enforce site+ev uniqueness."""

from __future__ import annotations

from alembic import op

revision = "043_heartbeat_ev_mappings_unique"
down_revision = "042_query_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM heartbeat_ev_mappings
        WHERE id IN (
            SELECT h1.id
            FROM heartbeat_ev_mappings h1
            INNER JOIN heartbeat_ev_mappings h2
              ON h1.site_id = h2.site_id
             AND h1.heartbeat_ev_id = h2.heartbeat_ev_id
             AND h1.id < h2.id
        )
        """
    )
    op.create_index(
        "uq_heartbeat_ev_mappings_site_ev",
        "heartbeat_ev_mappings",
        ["site_id", "heartbeat_ev_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_heartbeat_ev_mappings_site_ev", table_name="heartbeat_ev_mappings")
