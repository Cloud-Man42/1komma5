"""Add load priority for EV chargers in site energy orchestration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "036_ev_load_priority"
down_revision = "035_spa_actuator_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ev_chargers",
        sa.Column("load_priority", sa.Integer(), nullable=False, server_default="40"),
    )


def downgrade() -> None:
    op.drop_column("ev_chargers", "load_priority")
