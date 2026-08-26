"""Solar Intelligence Engine domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


INTELLIGENCE_MODEL_VERSION = "solar-intelligence-v2.0.0"


class ForecastStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class RadiationSourceConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class SampleQuality(StrEnum):
    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"
    REJECTED = "REJECTED"


class ProviderHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RadiationSample:
    ts_utc: datetime
    parameter: str
    value_wm2: float | None
    quality: SampleQuality = SampleQuality.GOOD
    provider: str = "smhi-strang"


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    ts_utc: datetime
    temperature_c: float | None = None
    cloud_cover_pct: float | None = None
    precipitation_mm: float | None = None
    humidity_pct: float | None = None
    wind_speed_ms: float | None = None
    provider: str = "smhi-snow"


@dataclass(frozen=True, slots=True)
class SolarGeometry:
    elevation_deg: float
    azimuth_deg: float
    sunrise: datetime | None
    sunset: datetime | None
    day_length_hours: float


@dataclass(frozen=True, slots=True)
class HourlyForecastPoint:
    timestamp: datetime
    physical_w: float
    corrected_w: float
    lower_w: float
    upper_w: float
    confidence: float
    ghi_wm2: float | None = None
    poa_wm2: float | None = None
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IntelligenceForecast:
    site_id: int
    generated_at: datetime
    model_version: str
    status: ForecastStatus
    expected_today_kwh: float
    remaining_today_kwh: float
    expected_tomorrow_kwh: float | None
    expected_day_after_kwh: float | None
    peak_power_w: float
    peak_time: datetime | None
    lower_today_kwh: float
    upper_today_kwh: float
    confidence: float
    confidence_label: str
    radiation_confidence: RadiationSourceConfidence
    hourly: tuple[HourlyForecastPoint, ...]
    physical_today_kwh: float
    learned_correction_pct: float
    weather_source: str
    last_known_good_at: datetime | None = None
    explainability: dict[str, float] = field(default_factory=dict)
    charging_signals: dict[str, float | str | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrainingSample:
    site_id: int
    sample_date: date
    hour_utc: int
    actual_kwh: float | None
    physical_kwh: float | None
    ghi_wm2: float | None
    dni_wm2: float | None
    dhi_wm2: float | None
    poa_wm2: float | None
    solar_elevation_deg: float | None
    cloud_cover_pct: float | None
    temperature_c: float | None
    quality: SampleQuality = SampleQuality.GOOD
    provenance: str | None = None


@dataclass(frozen=True, slots=True)
class SolarModelRecord:
    site_id: int
    role: str
    model_version: str
    trained_at: datetime
    sample_count: int
    mae: float | None = None
    mape: float | None = None
    wape: float | None = None
    rmse: float | None = None
    r2: float | None = None
    bias_pct: float | None = None
    features: dict[str, float] = field(default_factory=dict)
    coefficients: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PerformanceDaily:
    performance_date: date
    actual_kwh: float | None
    expected_kwh: float | None
    weather_normalized_kwh: float | None
    performance_ratio: float | None
    anomaly_score: float | None
    anomaly_flag: bool = False


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider: str
    status: ProviderHealthStatus
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
