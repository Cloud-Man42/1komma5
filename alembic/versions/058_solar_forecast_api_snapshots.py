"""Solar forecast API snapshot table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "058_solar_forecast_api_snapshots"
down_revision = "057_energy_control_interface"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solar_forecast_api_snapshots",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness", sa.String(length=16), nullable=False, server_default="DEGRADED"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_solar_forecast_api_snapshots_generated_at",
        "solar_forecast_api_snapshots",
        ["generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_solar_forecast_api_snapshots_generated_at", table_name="solar_forecast_api_snapshots")
    op.drop_table("solar_forecast_api_snapshots")
