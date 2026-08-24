"""Vehicle Halo correlation table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "028_vehicle_halo_correlation"
down_revision = "027_vehicle_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_halo_correlation",
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("charger_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("plugged_agreement", sa.Boolean(), nullable=True),
        sa.Column("charging_agreement", sa.Boolean(), nullable=True),
        sa.Column("power_delta_kw", sa.Float(), nullable=True),
        sa.Column("vehicle_power_kw", sa.Float(), nullable=True),
        sa.Column("halo_power_kw", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charger_id"], ["ev_chargers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("vehicle_id"),
    )


def downgrade() -> None:
    op.drop_table("vehicle_halo_correlation")
