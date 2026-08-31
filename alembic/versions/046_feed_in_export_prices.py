"""Add feed-in export price column and default sell mode to feed_in."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "046_feed_in_export_prices"
down_revision = "045_energy_economics_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("market_prices") as batch:
        batch.add_column(
            sa.Column("feed_in_price_eur_kwh", sa.Float(), nullable=True),
        )

    op.execute(
        sa.text(
            "UPDATE sites SET sell_pricing_mode = 'feed_in', sell_provider = '1KOMMA5' "
            "WHERE sell_pricing_mode = 'spot' AND sell_provider = ''"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("market_prices") as batch:
        batch.drop_column("feed_in_price_eur_kwh")
