from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class SolarSiteConfigurationModel(Base):
    __tablename__ = "solar_site_configurations"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    installed_peak_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    azimuth_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    tilt_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    inverter_max_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    system_loss_percent: Mapped[float] = mapped_column(Float, nullable=False, default=14.0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tilt_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    azimuth_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_forecast_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    solar_intelligence_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    commissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    panel_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    panel_wp: Mapped[float | None] = mapped_column(Float, nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="solar_configuration")


class SolarWeatherCacheModel(Base):
    __tablename__ = "solar_weather_cache"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="open-meteo")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SolarForecastRunModel(Base):
    __tablename__ = "solar_forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v1")
    quality: Mapped[str] = mapped_column(String(32), nullable=False, default="LOW")
    weather_source: Mapped[str] = mapped_column(String(16), nullable=False, default="live")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    remaining_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_tomorrow_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    peak_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lower_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weather_summary: Mapped[str] = mapped_column(String(256), nullable=False, default="")


class SolarForecastPointModel(Base):
    __tablename__ = "solar_forecast_points"

    run_id: Mapped[int] = mapped_column(ForeignKey("solar_forecast_runs.id", ondelete="CASCADE"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    baseline_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    corrected_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lower_bound_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_bound_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correction_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    gti_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class SolarForecastEvaluationModel(Base):
    __tablename__ = "solar_forecast_evaluations"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    forecasted_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    absolute_error_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    squared_error: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v1")


class SolarSitePerformanceProfileModel(Base):
    __tablename__ = "solar_site_performance_profiles"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    global_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    seasonal_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    hour_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    weather_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mape_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_kwh_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_pct_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastObservationModel(Base):
    __tablename__ = "solar_forecast_observations"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    forecast_date: Mapped[date] = mapped_column(Date, primary_key=True)
    forecast_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forecast_kwh_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_kwh_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weather_model: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cloud_cover_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_hourly_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    solar_radiation: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    sunshine_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    sunrise: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sunset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    weather_condition_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correction_factor_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_error_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    signed_error_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_absolute_error_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_completeness_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    physical_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    learned_correction_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    radiation_kwh_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v2")
    site_configuration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastModelProfileModel(Base):
    __tablename__ = "solar_forecast_model_profiles"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v2")
    historical_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_state: Mapped[str] = mapped_column(String(32), nullable=False, default="NO_DATA")
    mape_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_7d_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mape_30d_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mape_90d_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mae_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_mae_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_mae_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    improvement_pct_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    correction_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    seasonal_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_training_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarArrayModel(Base):
    __tablename__ = "solar_arrays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Main")
    capacity_kwp: Mapped[float] = mapped_column(Float, nullable=False)
    azimuth_degrees: Mapped[float] = mapped_column(Float, nullable=False, default=180.0)
    tilt_degrees: Mapped[float] = mapped_column(Float, nullable=False, default=35.0)


class SolarSiteConfigurationVersionModel(Base):
    __tablename__ = "solar_site_configuration_versions"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    config_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class SolarDailyForecastSnapshotModel(Base):
    __tablename__ = "solar_daily_forecast_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    forecast_date: Mapped[date] = mapped_column(Date, primary_key=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_kwh_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_kwh_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("solar_forecast_runs.id", ondelete="SET NULL"), nullable=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v2")
    weather_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarRadiationSampleModel(Base):
    __tablename__ = "solar_radiation_samples"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    parameter: Mapped[str] = mapped_column(String(32), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    value_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="GOOD")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SolarWeatherSnapshotModel(Base):
    __tablename__ = "solar_weather_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarTrainingSampleModel(Base):
    __tablename__ = "solar_training_samples"
    __table_args__ = (
        UniqueConstraint("site_id", "sample_date", "hour_utc", name="uq_solar_training_sample"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_date: Mapped[date] = mapped_column(Date, nullable=False)
    hour_utc: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    physical_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    ghi_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    dni_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    dhi_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    poa_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_elevation_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="GOOD")
    provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SolarModelRecordModel(Base):
    __tablename__ = "solar_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="challenger")
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    features_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    coefficients_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    configuration_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastHourlyModel(Base):
    __tablename__ = "solar_forecast_hourly"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    physical_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    corrected_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lower_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    breakdown_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SolarPerformanceDailyModel(Base):
    __tablename__ = "solar_performance_daily"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    performance_date: Mapped[date] = mapped_column(Date, primary_key=True)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_normalized_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarProviderHealthModel(Base):
    __tablename__ = "solar_provider_health"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(256), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastApiSnapshotModel(Base):
    __tablename__ = "solar_forecast_api_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    freshness: Mapped[str] = mapped_column(String(16), nullable=False, default="DEGRADED")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
