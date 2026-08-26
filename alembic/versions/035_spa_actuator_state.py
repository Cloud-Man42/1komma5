"""Spa actuator runtime state table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "035_spa_actuator_state"
down_revision = "034_spa_smart_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spa_actuator_state",
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="IDLE"),
        sa.Column("runtime_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("integration_degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("integration_degraded_message_sv", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["consumer_id"], ["energy_consumers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consumer_id"),
    )


def downgrade() -> None:
    op.drop_table("spa_actuator_state")
