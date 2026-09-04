"""Energy forecast snapshots for learning (price, load, solar)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "056_energy_forecast_snapshots"
down_revision = "055_price_engine_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "energy_forecast_snapshots",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("period_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("forecast_kind", sa.String(length=32), primary_key=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("forecast_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_energy_forecast_snapshots_site_kind_period",
        "energy_forecast_snapshots",
        ["site_id", "forecast_kind", "period_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_energy_forecast_snapshots_site_kind_period", table_name="energy_forecast_snapshots")
    op.drop_table("energy_forecast_snapshots")
