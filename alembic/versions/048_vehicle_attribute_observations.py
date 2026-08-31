"""Add vehicle attribute observations for Mercedes field discovery."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "048_vehicle_attribute_observations"
down_revision = "047_sell_contract_start_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_attribute_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "vehicle_id",
            sa.Integer(),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attribute_name", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="WS"),
        sa.Column("value_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("masked_sample", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_vehicle_attribute_observations_vehicle_id",
        "vehicle_attribute_observations",
        ["vehicle_id"],
    )
    op.create_index(
        "uq_vehicle_attribute_obs_vehicle_name_source",
        "vehicle_attribute_observations",
        ["vehicle_id", "attribute_name", "source"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_vehicle_attribute_obs_vehicle_name_source", table_name="vehicle_attribute_observations")
    op.drop_index("ix_vehicle_attribute_observations_vehicle_id", table_name="vehicle_attribute_observations")
    op.drop_table("vehicle_attribute_observations")
