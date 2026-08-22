"""Add site energy valuation settings and historical market prices."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "013_financial_stats"
down_revision: str | None = "012_drop_energy_devices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column(
            "fallback_purchase_price_sek_kwh",
            sa.Float(),
            nullable=False,
            server_default="2.0",
        ),
    )
    op.add_column(
        "sites",
        sa.Column(
            "export_compensation_sek_kwh",
            sa.Float(),
            nullable=False,
            server_default="0.8",
        ),
    )
    op.create_table(
        "market_prices",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("spot_price_sek_kwh", sa.Float(), nullable=False),
        sa.Column("all_in_price_sek_kwh", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("site_id", "recorded_at"),
    )
    op.create_index("ix_market_prices_recorded_at", "market_prices", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_market_prices_recorded_at", table_name="market_prices")
    op.drop_table("market_prices")
    op.drop_column("sites", "export_compensation_sek_kwh")
    op.drop_column("sites", "fallback_purchase_price_sek_kwh")
