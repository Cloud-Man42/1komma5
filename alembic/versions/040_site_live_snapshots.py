"""Site live snapshots read model."""

revision = "040_site_live_snapshots"
down_revision = "039_solar_intelligence_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    op.create_table(
        "site_live_snapshots",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness", sa.String(length=16), nullable=False, server_default="DEGRADED"),
        sa.Column("source_status_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_site_live_snapshots_generated_at", "site_live_snapshots", ["generated_at"])

    op.create_table(
        "energy_hourly",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("hour", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("solar_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consumption_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("import_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("export_kwh", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_energy_hourly_site_hour", "energy_hourly", ["site_id", "hour"])

    op.create_table(
        "energy_daily",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("solar_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consumption_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("import_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("export_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("import_cost_sek", sa.Float(), nullable=True),
        sa.Column("export_revenue_sek", sa.Float(), nullable=True),
    )
    op.create_index("ix_energy_daily_site_day", "energy_daily", ["site_id", "day"])


def downgrade() -> None:
    from alembic import op

    op.drop_index("ix_energy_daily_site_day", table_name="energy_daily")
    op.drop_table("energy_daily")
    op.drop_index("ix_energy_hourly_site_hour", table_name="energy_hourly")
    op.drop_table("energy_hourly")
    op.drop_index("ix_site_live_snapshots_generated_at", table_name="site_live_snapshots")
    op.drop_table("site_live_snapshots")
