"""Add per-site energy economics configuration for export revenue."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "045_energy_economics_config"
down_revision = "044_encrypt_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(
            sa.Column("energy_economics_country", sa.String(length=8), nullable=False, server_default="SE"),
        )
        batch.add_column(
            sa.Column("sell_pricing_mode", sa.String(length=16), nullable=False, server_default="spot"),
        )
        batch.add_column(
            sa.Column("sell_provider", sa.String(length=64), nullable=False, server_default=""),
        )
        batch.add_column(
            sa.Column("sell_adjustment_ore_per_kwh", sa.Float(), nullable=False, server_default="0"),
        )
        batch.add_column(
            sa.Column("sell_deduction_ore_per_kwh", sa.Float(), nullable=False, server_default="0"),
        )
        batch.add_column(
            sa.Column("grid_benefit_ore_per_kwh", sa.Float(), nullable=False, server_default="0"),
        )
        batch.add_column(
            sa.Column(
                "historical_tax_credit_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.drop_column("historical_tax_credit_enabled")
        batch.drop_column("grid_benefit_ore_per_kwh")
        batch.drop_column("sell_deduction_ore_per_kwh")
        batch.drop_column("sell_adjustment_ore_per_kwh")
        batch.drop_column("sell_provider")
        batch.drop_column("sell_pricing_mode")
        batch.drop_column("energy_economics_country")
