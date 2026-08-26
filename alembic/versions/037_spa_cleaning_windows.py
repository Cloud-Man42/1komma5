"""Add windows_json to flexible load plans and update spa max starts default."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "037_spa_cleaning_windows"
down_revision = "036_ev_load_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "flexible_load_plan",
        sa.Column("windows_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("flexible_load_plan", "windows_json")
