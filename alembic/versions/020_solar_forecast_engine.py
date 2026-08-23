"""Solar forecast engine tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "020_solar_forecast_engine"
down_revision = "019_smart_charging_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solar_site_configurations",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("installed_peak_power_kw", sa.Float(), nullable=True),
        sa.Column("azimuth_deg", sa.Float(), nullable=True),
        sa.Column("tilt_deg", sa.Float(), nullable=True),
        sa.Column("inverter_max_power_kw", sa.Float(), nullable=True),
        sa.Column("system_loss_percent", sa.Float(), nullable=False, server_default="14"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tilt_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("azimuth_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_forecast_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "solar_weather_cache",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("fetched_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="open-meteo"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "solar_forecast_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "model_version",
            sa.String(length=32),
            nullable=False,
            server_default="solar-forecast-v1",
        ),
        sa.Column("quality", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("weather_source", sa.String(length=16), nullable=False, server_default="live"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expected_today_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("remaining_today_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expected_tomorrow_kwh", sa.Float(), nullable=True),
        sa.Column("peak_power_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("peak_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lower_today_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upper_today_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weather_summary", sa.String(length=256), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solar_forecast_runs_site_id", "solar_forecast_runs", ["site_id"])
    op.create_index("ix_solar_forecast_runs_generated_at", "solar_forecast_runs", ["generated_at"])
    op.create_table(
        "solar_forecast_points",
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("solar_forecast_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("baseline_power_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("corrected_power_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expected_energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lower_bound_power_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upper_bound_power_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("correction_factor", sa.Float(), nullable=False, server_default="1"),
        sa.Column("gti_wm2", sa.Float(), nullable=True),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=True),
    )
    op.create_table(
        "solar_forecast_evaluations",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("bucket_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("forecasted_energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_energy_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("absolute_error_kwh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("percentage_error", sa.Float(), nullable=True),
        sa.Column("squared_error", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "model_version",
            sa.String(length=32),
            nullable=False,
            server_default="solar-forecast-v1",
        ),
    )
    op.create_table(
        "solar_site_performance_profiles",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("global_factor", sa.Float(), nullable=False, server_default="1"),
        sa.Column("seasonal_factors_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("hour_factors_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("weather_factors_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mape_7d", sa.Float(), nullable=True),
        sa.Column("mape_30d", sa.Float(), nullable=True),
        sa.Column("mae_kwh_30d", sa.Float(), nullable=True),
        sa.Column("bias_pct_30d", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("solar_site_performance_profiles")
    op.drop_table("solar_forecast_evaluations")
    op.drop_table("solar_forecast_points")
    op.drop_index("ix_solar_forecast_runs_generated_at", table_name="solar_forecast_runs")
    op.drop_index("ix_solar_forecast_runs_site_id", table_name="solar_forecast_runs")
    op.drop_table("solar_forecast_runs")
    op.drop_table("solar_weather_cache")
    op.drop_table("solar_site_configurations")
