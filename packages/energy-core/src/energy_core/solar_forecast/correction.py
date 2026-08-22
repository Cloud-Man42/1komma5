"""Local forecast correction engine."""

from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean

from energy_core.solar_forecast.constants import (
    MAX_CORRECTION_FACTOR,
    MIN_CORRECTION_FACTOR,
    MIN_SAMPLES_FOR_CORRECTION,
    SHRINKAGE_STRENGTH,
)
from energy_core.solar_forecast.historical import cloud_bucket, irradiance_bucket, recency_weight
from energy_core.solar_forecast.types import (
    PerformanceSample,
    SitePerformanceProfile,
    WeatherForecastPoint,
)


def shrink_factor(raw: float, sample_count: int) -> float:
    """Shrink correction toward 1.0 when sample count is low."""
    if sample_count <= 0:
        return 1.0
    weight = sample_count / (sample_count + SHRINKAGE_STRENGTH)
    return 1.0 + (raw - 1.0) * weight


def clamp_factor(value: float) -> float:
    return max(MIN_CORRECTION_FACTOR, min(MAX_CORRECTION_FACTOR, value))


def build_profile(samples: list[PerformanceSample], *, now: datetime | None = None) -> SitePerformanceProfile:
    now = now or datetime.now(UTC)
    if not samples:
        return SitePerformanceProfile(site_id=0, sample_count=0, updated_at=now)

    site_id = 0  # caller sets
    weighted_ratios: list[tuple[float, float]] = []
    seasonal: dict[int, list[tuple[float, float]]] = {}
    hourly: dict[int, list[tuple[float, float]]] = {}
    weather: dict[str, list[tuple[float, float]]] = {}

    for s in samples:
        age = (now - s.timestamp).total_seconds() / 86400.0
        w = recency_weight(age, now.month, s.month) * s.weight
        weighted_ratios.append((s.performance_ratio, w))
        seasonal.setdefault(s.month, []).append((s.performance_ratio, w))
        hourly.setdefault(s.hour, []).append((s.performance_ratio, w))
        key = f"{s.irradiance_bucket}_{s.cloud_bucket}"
        weather.setdefault(key, []).append((s.performance_ratio, w))

    global_factor = _weighted_mean(weighted_ratios)
    global_factor = shrink_factor(global_factor, len(samples))

    return SitePerformanceProfile(
        site_id=site_id,
        global_factor=clamp_factor(global_factor),
        seasonal_factors={m: clamp_factor(shrink_factor(_weighted_mean(v), len(v))) for m, v in seasonal.items()},
        hour_factors={h: clamp_factor(shrink_factor(_weighted_mean(v), len(v))) for h, v in hourly.items()},
        weather_factors={k: clamp_factor(shrink_factor(_weighted_mean(v), len(v))) for k, v in weather.items()},
        sample_count=len(samples),
        updated_at=now,
    )


def _weighted_mean(pairs: list[tuple[float, float]]) -> float:
    if not pairs:
        return 1.0
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return mean(r for r, _ in pairs)
    return sum(r * w for r, w in pairs) / total_w


class SolarForecastCorrectionEngine:
    def correction_factor(
        self,
        profile: SitePerformanceProfile,
        point: WeatherForecastPoint,
        timestamp: datetime,
    ) -> float:
        if profile.sample_count < MIN_SAMPLES_FOR_CORRECTION:
            return 1.0

        local = timestamp.astimezone(UTC)
        month = local.month
        hour = local.hour
        irr = point.gti_wm2 or point.ghi_wm2 or 0.0
        wkey = f"{irradiance_bucket(irr)}_{cloud_bucket(point.cloud_cover_pct)}"

        factors = [profile.global_factor]
        if month in profile.seasonal_factors:
            factors.append(profile.seasonal_factors[month])
        if hour in profile.hour_factors:
            factors.append(profile.hour_factors[hour])
        if wkey in profile.weather_factors:
            factors.append(profile.weather_factors[wkey])

        # Hierarchical blend: geometric mean of available factors, then clamp
        product = 1.0
        for f in factors:
            product *= f
        combined = product ** (1.0 / len(factors)) if factors else 1.0
        return clamp_factor(combined)

    def apply(
        self,
        baseline_power_w: float,
        profile: SitePerformanceProfile,
        point: WeatherForecastPoint,
        timestamp: datetime,
    ) -> tuple[float, float]:
        factor = self.correction_factor(profile, point, timestamp)
        corrected = max(0.0, baseline_power_w * factor)
        return corrected, factor
