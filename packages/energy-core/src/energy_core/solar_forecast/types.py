"""Solar forecast domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from energy_core.config import Settings, get_settings

ForecastQuality = Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT_DATA"]
WeatherSource = Literal["live", "cache", "fallback"]
ConfidenceLabel = Literal["Low", "Medium", "High"]

MODEL_VERSION = "solar-forecast-v2"
INTERVAL_MINUTES = 15


class ModelState(StrEnum):
    NO_DATA = "NO_DATA"
    LEARNING = "LEARNING"
    PRELIMINARY = "PRELIMINARY"
    CALIBRATED = "CALIBRATED"
    MATURE = "MATURE"


def resolve_model_state(sample_count: int, settings: Settings | None = None) -> ModelState:
    """Map historical training sample count to model lifecycle state."""
    cfg = settings or get_settings()
    if sample_count <= 0:
        return ModelState.NO_DATA
    if sample_count < cfg.solar_forecast_min_samples_preliminary:
        return ModelState.LEARNING
    if sample_count < cfg.solar_forecast_min_samples_calibrated:
        return ModelState.PRELIMINARY
    if sample_count < cfg.solar_forecast_min_samples_mature:
        return ModelState.CALIBRATED
    return ModelState.MATURE


def confidence_label_from_score(score: float | None) -> ConfidenceLabel | None:
    if score is None:
        return None
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


@dataclass(frozen=True, slots=True)
class SolarSiteConfiguration:
    site_id: int
    latitude: float
    longitude: float
    installed_peak_power_kw: float
    azimuth_deg: float | None = None
    tilt_deg: float | None = None
    inverter_max_power_kw: float | None = None
    system_loss_percent: float = 14.0
    enabled: bool = False
    tilt_estimated: bool = False
    azimuth_estimated: bool = False
    timezone: str = "UTC"
    solar_intelligence_enabled: bool = False

    def is_complete(self) -> bool:
        return (
            self.enabled
            and -90.0 <= self.latitude <= 90.0
            and -180.0 <= self.longitude <= 180.0
            and self.installed_peak_power_kw > 0
        )


@dataclass(frozen=True, slots=True)
class WeatherForecastPoint:
    timestamp: datetime
    ghi_wm2: float | None = None
    direct_radiation_wm2: float | None = None
    diffuse_radiation_wm2: float | None = None
    gti_wm2: float | None = None
    cloud_cover_pct: float | None = None
    temperature_c: float | None = None
    precipitation_mm: float | None = None
    weather_code: int | None = None
    sunshine_duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    site_id: int
    fetched_at: datetime
    provider: str
    points: tuple[WeatherForecastPoint, ...]
    source: WeatherSource = "live"


@dataclass(frozen=True, slots=True)
class SolarForecastPoint:
    timestamp: datetime
    baseline_power_w: float
    corrected_power_w: float
    expected_energy_kwh: float
    lower_bound_power_w: float
    upper_bound_power_w: float
    confidence: float
    gti_wm2: float | None = None
    cloud_cover_pct: float | None = None
    correction_factor: float = 1.0


@dataclass(frozen=True, slots=True)
class SolarArray:
    site_id: int
    name: str
    capacity_kwp: float
    azimuth_degrees: float
    tilt_degrees: float
    array_id: int | None = None


@dataclass(frozen=True, slots=True)
class SeasonalCorrectionProfile:
    """Schema-ready seasonal factors keyed by month (1-12)."""

    factors: dict[int, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SolarForecastObservation:
    site_id: int
    forecast_date: date
    forecast_generated_at: datetime | None = None
    forecast_kwh_raw: float | None = None
    forecast_kwh_corrected: float | None = None
    actual_kwh: float | None = None
    weather_provider: str | None = None
    weather_model: str | None = None
    cloud_cover_avg: float | None = None
    cloud_cover_hourly: list[float] | None = None
    solar_radiation: float | None = None
    temperature_avg: float | None = None
    precipitation: float | None = None
    sunshine_duration: float | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None
    weather_condition_bucket: str | None = None
    correction_factor_used: float | None = None
    absolute_error_kwh: float | None = None
    percentage_error: float | None = None
    signed_error_kwh: float | None = None
    raw_absolute_error_kwh: float | None = None
    raw_percentage_error: float | None = None
    data_completeness_pct: float | None = None
    training_eligible: bool = True
    exclusion_reason: str | None = None
    physical_kwh: float | None = None
    learned_correction_pct: float | None = None
    radiation_kwh_m2: float | None = None
    provenance: str | None = None
    model_version: str = MODEL_VERSION
    site_configuration_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SolarForecastModelProfile:
    site_id: int
    model_version: str = MODEL_VERSION
    historical_samples: int = 0
    model_state: ModelState = ModelState.NO_DATA
    mape_7d: float | None = None
    mape_30d: float | None = None
    mape_90d: float | None = None
    mape_7d_valid_days: int = 0
    mape_30d_valid_days: int = 0
    mape_90d_valid_days: int = 0
    mae_7d: float | None = None
    mae_30d: float | None = None
    mae_90d: float | None = None
    bias_7d: float | None = None
    bias_30d: float | None = None
    bias_90d: float | None = None
    wape_7d: float | None = None
    wape_30d: float | None = None
    wape_90d: float | None = None
    rmse_7d: float | None = None
    rmse_30d: float | None = None
    rmse_90d: float | None = None
    r2_7d: float | None = None
    r2_30d: float | None = None
    r2_90d: float | None = None
    raw_mae_30d: float | None = None
    corrected_mae_30d: float | None = None
    improvement_pct_30d: float | None = None
    correction_factor: float = 1.0
    confidence_score: float | None = None
    seasonal_factors: dict[int, float] = field(default_factory=dict)
    last_training_at: datetime | None = None
    last_evaluation_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SolarForecast:
    site_id: int
    generated_at: datetime
    model_version: str
    quality: ForecastQuality
    weather_source: WeatherSource
    expected_today_kwh: float
    remaining_today_kwh: float
    expected_tomorrow_kwh: float | None
    peak_power_w: float
    peak_time: datetime | None
    confidence: float
    lower_today_kwh: float
    upper_today_kwh: float
    weather_summary: str
    points: tuple[SolarForecastPoint, ...]
    raw_forecast_today_kwh: float = 0.0
    raw_forecast_tomorrow_kwh: float | None = None
    corrected_forecast_today_kwh: float = 0.0
    corrected_forecast_tomorrow_kwh: float | None = None
    correction_factor: float = 1.0
    model_state: ModelState = ModelState.NO_DATA
    confidence_score: float | None = None
    historical_samples: int = 0


@dataclass(frozen=True, slots=True)
class PerformanceSample:
    timestamp: datetime
    baseline_energy_kwh: float
    actual_energy_kwh: float
    performance_ratio: float
    month: int
    hour: int
    irradiance_bucket: str
    cloud_bucket: str
    is_anomaly: bool = False
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class SitePerformanceProfile:
    site_id: int
    global_factor: float = 1.0
    seasonal_factors: dict[int, float] = field(default_factory=dict)
    hour_factors: dict[int, float] = field(default_factory=dict)
    weather_factors: dict[str, float] = field(default_factory=dict)
    sample_count: int = 0
    mape_7d: float | None = None
    mape_30d: float | None = None
    mae_kwh_30d: float | None = None
    bias_pct_30d: float | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ForecastEvaluation:
    site_id: int
    forecast_timestamp: datetime
    bucket_start: datetime
    forecasted_energy_kwh: float
    actual_energy_kwh: float
    absolute_error_kwh: float
    percentage_error: float | None
    squared_error: float
    model_version: str


@dataclass(frozen=True, slots=True)
class ForecastAccuracySummary:
    site_id: int
    period_days: int
    mae_kwh: float | None
    mape_pct: float | None
    rmse_kwh: float | None
    bias_pct: float | None
    sample_count: int
    model_version: str


@dataclass(frozen=True, slots=True)
class SolarEnergyBudget:
    site_id: int
    forecast_solar_kwh: float
    expected_house_consumption_kwh: float | None
    ev_required_kwh: float | None
    battery_available_capacity_kwh: float | None
    expected_surplus_kwh: float | None
    expected_deficit_kwh: float | None
    confidence: float
    quality: ForecastQuality
    consumption_source: Literal["historical", "unavailable"] = "unavailable"


@dataclass(frozen=True, slots=True)
class SolarChargingPlan:
    """Advisory plan for smart charging — does not control live current."""

    expected_usable_solar_kwh: float
    planning_solar_kwh: float
    quality: ForecastQuality
    confidence: float
    expected_solar_window_start: datetime | None
    expected_solar_window_end: datetime | None
    cheapest_grid_window: str | None
    explanation_sv: str
    reason_code: str
    # True when enough solar is expected before the deadline to hold off the grid.
    solar_first: bool = False
