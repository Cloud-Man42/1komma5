"""Drop unused bridge_mode column from ev_chargers."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "017_drop_bridge_mode"
down_revision = "016_smart_charging_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("ev_chargers", "bridge_mode")


def downgrade() -> None:
    op.add_column(
        "ev_chargers",
        sa.Column("bridge_mode", sa.String(length=32), nullable=False, server_default="auto"),
    )
