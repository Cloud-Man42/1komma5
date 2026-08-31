"""Add export contract start date per site."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "047_sell_contract_start_date"
down_revision = "046_feed_in_export_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(
            sa.Column("sell_contract_start_date", sa.Date(), nullable=True),
        )

    op.execute(
        sa.text(
            "UPDATE sites SET sell_contract_start_date = '2026-08-25' WHERE slug = 'akarp'"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.drop_column("sell_contract_start_date")
