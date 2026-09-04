"""Financial daily aggregates."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "059_financial_daily"
down_revision = "058_solar_forecast_api_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_daily",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("solar_self_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("battery_self_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("export_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("import_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("solar_savings_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("battery_savings_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_import_cost_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("market_priced_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("priced_denominator_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("energy_sale_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grid_benefit_sek", sa.Float(), nullable=False, server_default="0"),
        sa.Column("spot_priced_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fallback_priced_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("negative_price_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contracted_export_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uncontracted_export_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("site_id", "day"),
    )


def downgrade() -> None:
    op.drop_table("financial_daily")
