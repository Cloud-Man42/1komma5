"""Solar Intelligence Engine — tables and site config extensions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "039_solar_intelligence_engine"
down_revision = "038_spa_filter_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "solar_site_configurations",
        sa.Column("solar_intelligence_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "solar_site_configurations",
        sa.Column("commissioning_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "solar_site_configurations",
        sa.Column("panel_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "solar_site_configurations",
        sa.Column("panel_wp", sa.Float(), nullable=True),
    )
    op.add_column(
        "solar_site_configurations",
        sa.Column("country_code", sa.String(length=2), nullable=True),
    )

    op.add_column(
        "solar_forecast_observations",
        sa.Column("physical_kwh", sa.Float(), nullable=True),
    )
    op.add_column(
        "solar_forecast_observations",
        sa.Column("learned_correction_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "solar_forecast_observations",
        sa.Column("radiation_kwh_m2", sa.Float(), nullable=True),
    )
    op.add_column(
        "solar_forecast_observations",
        sa.Column("provenance", sa.String(length=32), nullable=True),
    )

    op.add_column("solar_forecast_model_profiles", sa.Column("wape_7d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("wape_30d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("wape_90d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("rmse_7d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("rmse_30d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("rmse_90d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("r2_7d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("r2_30d", sa.Float(), nullable=True))
    op.add_column("solar_forecast_model_profiles", sa.Column("r2_90d", sa.Float(), nullable=True))

    op.create_table(
        "solar_daily_forecast_snapshots",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("forecast_date", sa.Date(), primary_key=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_kwh_raw", sa.Float(), nullable=True),
        sa.Column("forecast_kwh_corrected", sa.Float(), nullable=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("solar_forecast_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="solar-forecast-v2"),
        sa.Column("weather_source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "solar_radiation_samples",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ts_utc", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("parameter", sa.String(length=32), primary_key=True),
        sa.Column("provider", sa.String(length=32), primary_key=True),
        sa.Column("value_wm2", sa.Float(), nullable=True),
        sa.Column("quality", sa.String(length=16), nullable=False, server_default="GOOD"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_solar_radiation_samples_site_ts", "solar_radiation_samples", ["site_id", "ts_utc"])

    op.create_table(
        "solar_weather_snapshots",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ts_utc", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("provider", sa.String(length=32), primary_key=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=True),
        sa.Column("precipitation_mm", sa.Float(), nullable=True),
        sa.Column("humidity_pct", sa.Float(), nullable=True),
        sa.Column("wind_speed_ms", sa.Float(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "solar_training_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sample_date", sa.Date(), nullable=False),
        sa.Column("hour_utc", sa.Integer(), nullable=False),
        sa.Column("actual_kwh", sa.Float(), nullable=True),
        sa.Column("physical_kwh", sa.Float(), nullable=True),
        sa.Column("ghi_wm2", sa.Float(), nullable=True),
        sa.Column("dni_wm2", sa.Float(), nullable=True),
        sa.Column("dhi_wm2", sa.Float(), nullable=True),
        sa.Column("poa_wm2", sa.Float(), nullable=True),
        sa.Column("solar_elevation_deg", sa.Float(), nullable=True),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("quality", sa.String(length=16), nullable=False, server_default="GOOD"),
        sa.Column("provenance", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("site_id", "sample_date", "hour_utc", name="uq_solar_training_sample"),
    )

    op.create_table(
        "solar_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="challenger"),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_from", sa.Date(), nullable=True),
        sa.Column("training_to", sa.Date(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("mape", sa.Float(), nullable=True),
        sa.Column("wape", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("r2", sa.Float(), nullable=True),
        sa.Column("bias_pct", sa.Float(), nullable=True),
        sa.Column("features_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("coefficients_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("configuration_hash", sa.String(length=64), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "solar_forecast_hourly",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("physical_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("corrected_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lower_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upper_w", sa.Float(), nullable=False, server_default="0"),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("breakdown_json", sa.Text(), nullable=True),
    )

    op.create_table(
        "solar_performance_daily",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("performance_date", sa.Date(), primary_key=True),
        sa.Column("actual_kwh", sa.Float(), nullable=True),
        sa.Column("expected_kwh", sa.Float(), nullable=True),
        sa.Column("weather_normalized_kwh", sa.Float(), nullable=True),
        sa.Column("performance_ratio", sa.Float(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("anomaly_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "solar_provider_health",
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(length=32), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=256), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("solar_provider_health")
    op.drop_table("solar_performance_daily")
    op.drop_table("solar_forecast_hourly")
    op.drop_table("solar_models")
    op.drop_table("solar_training_samples")
    op.drop_table("solar_weather_snapshots")
    op.drop_index("ix_solar_radiation_samples_site_ts", table_name="solar_radiation_samples")
    op.drop_table("solar_radiation_samples")
    op.drop_table("solar_daily_forecast_snapshots")

    op.drop_column("solar_forecast_model_profiles", "r2_90d")
    op.drop_column("solar_forecast_model_profiles", "r2_30d")
    op.drop_column("solar_forecast_model_profiles", "r2_7d")
    op.drop_column("solar_forecast_model_profiles", "rmse_90d")
    op.drop_column("solar_forecast_model_profiles", "rmse_30d")
    op.drop_column("solar_forecast_model_profiles", "rmse_7d")
    op.drop_column("solar_forecast_model_profiles", "wape_90d")
    op.drop_column("solar_forecast_model_profiles", "wape_30d")
    op.drop_column("solar_forecast_model_profiles", "wape_7d")

    op.drop_column("solar_forecast_observations", "provenance")
    op.drop_column("solar_forecast_observations", "radiation_kwh_m2")
    op.drop_column("solar_forecast_observations", "learned_correction_pct")
    op.drop_column("solar_forecast_observations", "physical_kwh")

    op.drop_column("solar_site_configurations", "country_code")
    op.drop_column("solar_site_configurations", "panel_wp")
    op.drop_column("solar_site_configurations", "panel_count")
    op.drop_column("solar_site_configurations", "commissioning_date")
    op.drop_column("solar_site_configurations", "solar_intelligence_enabled")
