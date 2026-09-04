"""Price engine foundation tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "055_price_engine_foundation"
down_revision = "054_vehicle_session_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(sa.Column("price_area", sa.String(length=8), nullable=False, server_default="SE4"))
        batch.add_column(
            sa.Column("optimization_mode", sa.String(length=32), nullable=False, server_default="MONITOR_ONLY")
        )

    op.create_table(
        "price_periods",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("period_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_area", sa.String(length=8), nullable=False, server_default="SE4"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="SEK"),
        sa.Column("market_price_sek_kwh", sa.Float(), nullable=True),
        sa.Column("import_price_sek_kwh", sa.Float(), nullable=True),
        sa.Column("export_price_sek_kwh", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="heartbeat"),
        sa.Column("quality", sa.String(length=16), nullable=False, server_default="REAL"),
        sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("components_json", sa.Text(), nullable=True),
    )
    op.create_index("ix_price_periods_site_period", "price_periods", ["site_id", "period_start"])

    op.create_table(
        "price_engine_state",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_market_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_import_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_export_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("missing_periods_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_age_seconds", sa.Integer(), nullable=True),
        sa.Column("optimization_mode", sa.String(length=32), nullable=False, server_default="MONITOR_ONLY"),
    )

    op.execute(
        sa.text(
            "UPDATE sites SET price_area = 'DK2' "
            "WHERE energy_economics_country = 'DK' OR slug LIKE '%denmark%'"
        )
    )


def downgrade() -> None:
    op.drop_table("price_engine_state")
    op.drop_index("ix_price_periods_site_period", table_name="price_periods")
    op.drop_table("price_periods")
    with op.batch_alter_table("sites") as batch:
        batch.drop_column("optimization_mode")
        batch.drop_column("price_area")
