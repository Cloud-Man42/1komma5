"""Confidence and forecast interval calculation."""

from __future__ import annotations

from datetime import datetime

from energy_core.solar_forecast.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
)
from energy_core.solar_forecast.types import (
    ForecastQuality,
    SitePerformanceProfile,
    WeatherForecast,
)


def cloud_variability(points_cloud: list[float | None]) -> float:
    values = [c for c in points_cloud if c is not None]
    if len(values) < 2:
        return 0.5
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return min(1.0, (variance**0.5) / 50.0)


def horizon_penalty(hours_ahead: float) -> float:
    if hours_ahead <= 6:
        return 0.0
    if hours_ahead <= 24:
        return 0.15
    if hours_ahead <= 48:
        return 0.25
    return 0.35


class SolarForecastConfidenceService:
    def compute_point_confidence(
        self,
        *,
        hours_ahead: float,
        weather_source: str,
        profile: SitePerformanceProfile,
        cloud_var: float,
        cache_age_minutes: float = 0.0,
    ) -> float:
        score = 1.0
        score -= horizon_penalty(hours_ahead)
        score -= cloud_var * 0.2

        if weather_source == "cache":
            score -= min(0.15, cache_age_minutes / 120.0 * 0.15)
        elif weather_source == "fallback":
            score -= 0.35

        if profile.sample_count < 5:
            score -= 0.25
        elif profile.sample_count < 30:
            score -= 0.10
        elif profile.sample_count >= 120:
            score += 0.05

        if profile.mape_30d is not None and profile.mape_30d > 20:
            score -= 0.10

        return max(0.05, min(0.98, score))

    def quality_from_confidence(self, confidence: float) -> ForecastQuality:
        if confidence >= CONFIDENCE_HIGH:
            return "HIGH"
        if confidence >= CONFIDENCE_MEDIUM:
            return "MEDIUM"
        if confidence >= 0.35:
            return "LOW"
        return "INSUFFICIENT_DATA"

    def interval_bounds(
        self,
        corrected_power_w: float,
        confidence: float,
        profile: SitePerformanceProfile,
        *,
        max_power_w: float | None = None,
    ) -> tuple[float, float]:
        # Base margin from confidence
        margin_pct = 0.35 * (1.0 - confidence) + 0.08
        if profile.mape_30d is not None:
            margin_pct = max(margin_pct, profile.mape_30d / 100.0)

        lower = max(0.0, corrected_power_w * (1.0 - margin_pct))
        upper = corrected_power_w * (1.0 + margin_pct)
        if max_power_w is not None:
            upper = min(upper, max_power_w)
        return lower, upper

    def aggregate_confidence(self, point_confidences: list[float]) -> float:
        if not point_confidences:
            return 0.0
        return sum(point_confidences) / len(point_confidences)

    def weather_summary(self, weather: WeatherForecast, *, now: datetime) -> str:
        if not weather.points:
            return "Ingen väderdata tillgänglig"
        upcoming = [p for p in weather.points if p.timestamp >= now][:8]
        if not upcoming:
            upcoming = list(weather.points[:8])
        clouds = [p.cloud_cover_pct for p in upcoming if p.cloud_cover_pct is not None]
        if not clouds:
            return "Sol förhållanden: okända"
        avg = sum(clouds) / len(clouds)
        if avg < 30:
            return "Sol förhållanden: bra"
        if avg < 60:
            return "Delvis molnigt"
        return "Molnigt — lägre solproduktion förväntas"
