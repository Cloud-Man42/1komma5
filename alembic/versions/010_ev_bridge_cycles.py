"""Add bridge cycle telemetry for charging savings statistics."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_ev_bridge_cycles"
down_revision: Union[str, None] = "009_ev_charger_local_prefs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ev_bridge_cycles",
        sa.Column("charger_id", sa.Integer(), sa.ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_current_a", sa.Float(), nullable=False, server_default="0"),
        sa.Column("price_kwh", sa.Float(), nullable=True),
        sa.Column("policy_mode", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("decision_reason", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("override_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("vehicle_connected", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("charger_id", "recorded_at"),
    )
    op.create_index("ix_ev_bridge_cycles_charger_recorded", "ev_bridge_cycles", ["charger_id", "recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_ev_bridge_cycles_charger_recorded", table_name="ev_bridge_cycles")
    op.drop_table("ev_bridge_cycles")
