"""Rename market price columns to reflect EUR storage."""

from __future__ import annotations

from alembic import op

revision = "041_market_price_eur_columns"
down_revision = "040_site_live_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("market_prices", "spot_price_sek_kwh", new_column_name="spot_price_eur_kwh")
    op.alter_column("market_prices", "all_in_price_sek_kwh", new_column_name="all_in_price_eur_kwh")


def downgrade() -> None:
    op.alter_column("market_prices", "spot_price_eur_kwh", new_column_name="spot_price_sek_kwh")
    op.alter_column("market_prices", "all_in_price_eur_kwh", new_column_name="all_in_price_sek_kwh")
