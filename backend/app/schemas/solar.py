from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class SolarSiteConfigResponse(BaseModel):
    site_slug: str
    latitude: float | None = None
    longitude: float | None = None
    installed_peak_power_kw: float | None = None
    azimuth_deg: float | None = None
    tilt_deg: float | None = None
    inverter_max_power_kw: float | None = None
    system_loss_percent: float = 14.0
    enabled: bool = False
    tilt_estimated: bool = False
    azimuth_estimated: bool = False
    complete: bool = False
    solar_intelligence_enabled: bool = False


class SolarSiteConfigUpdate(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    installed_peak_power_kw: float | None = None
    azimuth_deg: float | None = None
    tilt_deg: float | None = None
    inverter_max_power_kw: float | None = None
    system_loss_percent: float | None = Field(default=None, ge=0, le=50)
    enabled: bool = False
    tilt_estimated: bool = False
    azimuth_estimated: bool = False
    solar_intelligence_enabled: bool | None = None


class SolarForecastPointResponse(BaseModel):
    timestamp: datetime
    baseline_power_w: float
    corrected_power_w: float
    expected_energy_kwh: float
    lower_bound_power_w: float
    upper_bound_power_w: float
    confidence: float
    correction_factor: float = 1.0


class SolarForecastResponse(BaseModel):
    site_id: int
    generated_at: datetime
    model_version: str
    quality: str
    weather_source: str
    expected_today_kwh: float
    remaining_today_kwh: float
    expected_tomorrow_kwh: float | None = None
    peak_power_w: float
    peak_time: datetime | None = None
    confidence: float
    lower_today_kwh: float
    upper_today_kwh: float
    weather_summary: str
    actual_today_kwh: float = 0.0
    forecast_so_far_kwh: float = 0.0
    remaining_vs_expected_kwh: float = 0.0
    raw_forecast_today_kwh: float = 0.0
    raw_forecast_so_far_kwh: float = 0.0
    raw_forecast_tomorrow_kwh: float | None = None
    corrected_forecast_today_kwh: float = 0.0
    corrected_forecast_tomorrow_kwh: float | None = None
    correction_factor: float = 1.0
    model_state: str = "NO_DATA"
    confidence_score: float | None = None
    confidence_label: str | None = None
    historical_samples: int = 0
    production_days_observed: int = 0
    age_seconds: float = 0.0
    freshness: str = "LIVE"
    stale: bool = False
    snapshot_generated_at: datetime | None = None
    points: list[SolarForecastPointResponse] = Field(default_factory=list)


class SolarAccuracyResponse(BaseModel):
    site_slug: str
    model_version: str
    model_state: str = "NO_DATA"
    mape_7d_pct: float | None = None
    mape_30d_pct: float | None = None
    mape_7d_valid_days: int = 0
    mape_30d_valid_days: int = 0
    mae_kwh_7d: float | None = None
    mae_kwh_30d: float | None = None
    bias_pct_30d: float | None = None
    sample_count_30d: int = 0
    historical_samples: int = 0
    production_days_observed: int = 0
    correction_factor: float = 1.0
    confidence_score: float | None = None
    confidence_label: str | None = None
    metrics_insufficient: bool = True
    raw_mae_30d: float | None = None
    corrected_mae_30d: float | None = None
    improvement_pct_30d: float | None = None
    wape_7d_pct: float | None = None
    wape_30d_pct: float | None = None
    rmse_kwh_7d: float | None = None
    rmse_kwh_30d: float | None = None
    r2_30d: float | None = None
    insufficient_reason: str | None = None
    min_samples_for_calibrated: int = 30


class SolarForecastObservationResponse(BaseModel):
    forecast_date: date
    forecast_kwh_raw: float | None = None
    forecast_kwh_corrected: float | None = None
    actual_kwh: float | None = None
    absolute_error_kwh: float | None = None
    raw_absolute_error_kwh: float | None = None
    percentage_error: float | None = None
    data_completeness_pct: float | None = None
    correction_factor_used: float | None = None
    weather_condition_bucket: str | None = None
    training_eligible: bool = True
    exclusion_reason: str | None = None
    model_version: str


class SolarDiagnosticsResponse(BaseModel):
    site_slug: str
    observations: list[SolarForecastObservationResponse] = Field(default_factory=list)


class SolarEnergyBudgetResponse(BaseModel):
    site_slug: str
    forecast_solar_kwh: float
    expected_house_consumption_kwh: float | None = None
    expected_surplus_kwh: float | None = None
    expected_deficit_kwh: float | None = None
    confidence: float
    quality: str
    consumption_source: str = "unavailable"


class SolarHourlyPointResponse(BaseModel):
    timestamp: datetime
    physical_w: float
    corrected_w: float
    lower_w: float
    upper_w: float
    confidence: float


class SolarHourlyForecastResponse(BaseModel):
    site_slug: str
    points: list[SolarHourlyPointResponse] = Field(default_factory=list)


class SolarPerformanceResponse(BaseModel):
    site_slug: str
    days: list[dict] = Field(default_factory=list)
    headline_ratio: float | None = None
    today_deviation_pct: float | None = None
    week_avg: float | None = None
    month_avg: float | None = None
    quarter_avg: float | None = None
    ytd_avg: float | None = None
    raw_forecast_so_far_kwh: float | None = None
    actual_today_kwh: float | None = None


class SolarRadiationResponse(BaseModel):
    site_slug: str
    provider: str
    samples: list[dict] = Field(default_factory=list)


class DmiForecastPointResponse(BaseModel):
    timestamp: datetime
    ghi_wm2: float | None = None
    dhi_wm2: float | None = None
    temperature_c: float | None = None
    cloud_cover_pct: float | None = None
    precipitation_mm: float | None = None
    humidity_pct: float | None = None
    wind_speed_ms: float | None = None


class DmiForecastResponse(BaseModel):
    site_slug: str
    provider: str = "dmi-harmonie"
    country_code: str
    points: list[DmiForecastPointResponse] = Field(default_factory=list)


class SolarModelResponse(BaseModel):
    site_slug: str
    model_version: str | None = None
    sample_count: int = 0
    trained_at: datetime | None = None
    role: str | None = None


class SolarModelMetricsResponse(BaseModel):
    site_slug: str
    model_version: str
    mae: float | None = None
    mape: float | None = None
    wape: float | None = None
    rmse: float | None = None
    r2: float | None = None
    bias_pct: float | None = None
    metrics_insufficient: bool = True
    insufficient_reason: str | None = None
    historical_samples: int = 0


class SolarProviderStatusResponse(BaseModel):
    site_slug: str
    providers: list[dict] = Field(default_factory=list)


class SolarIntelligenceForecastResponse(BaseModel):
    site_slug: str
    expected_today_kwh: float = 0.0
    status: str = "UNAVAILABLE"
    point_count: int = 0


class SolarWeatherHourResponse(BaseModel):
    timestamp: datetime
    temperature_c: float | None = None
    cloud_cover_pct: float | None = None
    wind_speed_ms: float | None = None
    relative_humidity_pct: float | None = None
    precipitation_mm: float | None = None
    ghi_wm2: float | None = None
    weather_code: int | None = None
    condition_sv: str = "Okänt"
    condition_icon: str = "unknown"
    forecast_power_w: float | None = None


class SolarWeatherResponse(BaseModel):
    site_slug: str
    provider: str
    source: str
    fetched_at: datetime
    cache_age_minutes: float = 0.0
    sunrise: datetime | None = None
    sunset: datetime | None = None
    current: SolarWeatherHourResponse | None = None
    solar_impact_sv: str = ""
    hours: list[SolarWeatherHourResponse] = Field(default_factory=list)
