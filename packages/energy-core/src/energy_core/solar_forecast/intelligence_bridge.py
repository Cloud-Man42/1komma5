"""Bridge solar intelligence hourly forecasts into v2 SolarForecast storage/API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.solar_forecast_repo import SolarConfigRecord, SolarForecastRepository, _to_domain_config
from energy_core.solar_forecast.extended_forecast import build_extended_forecast_points
from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider
from energy_core.solar_forecast.types import (
    MODEL_VERSION,
    ForecastQuality,
    SolarForecast,
    SolarForecastPoint,
    SolarSiteConfiguration,
    WeatherSource,
)
from energy_core.solar_intelligence.types import ForecastStatus, IntelligenceForecast

logger = logging.getLogger(__name__)


def _normalize_confidence(score: float) -> float:
    """Map intelligence confidence (0–100 or 0–1) to v2 contract scale 0–1."""
    if score > 1.0:
        return max(0.0, min(1.0, score / 100.0))
    return max(0.0, min(1.0, score))


def intelligence_to_v2_points(intelligence: IntelligenceForecast) -> tuple[SolarForecastPoint, ...]:
    points: list[SolarForecastPoint] = []
    for hp in intelligence.hourly:
        ts = hp.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        energy = hp.corrected_w / 1000.0
        factor = hp.corrected_w / hp.physical_w if hp.physical_w > 0 else 1.0
        points.append(
            SolarForecastPoint(
                timestamp=ts,
                baseline_power_w=hp.physical_w,
                corrected_power_w=hp.corrected_w,
                expected_energy_kwh=energy,
                lower_bound_power_w=hp.lower_w,
                upper_bound_power_w=hp.upper_w,
                confidence=_normalize_confidence(hp.confidence),
                gti_wm2=hp.poa_wm2 or hp.ghi_wm2,
                correction_factor=factor,
            )
        )
    return tuple(points)


def _map_quality(status: ForecastStatus, confidence: float) -> ForecastQuality:
    if status == ForecastStatus.UNAVAILABLE:
        return "INSUFFICIENT_DATA"
    if status == ForecastStatus.DEGRADED or confidence < 0.45:
        return "LOW"
    if confidence < 0.75:
        return "MEDIUM"
    return "HIGH"


def compose_solar_forecast(
    site: SolarSiteConfiguration,
    intelligence: IntelligenceForecast,
    extended: tuple[SolarForecastPoint, ...],
) -> SolarForecast:
    near = intelligence_to_v2_points(intelligence)
    seen = {p.timestamp for p in near}
    merged = list(near)
    for point in extended:
        if point.timestamp not in seen:
            merged.append(point)
            seen.add(point.timestamp)
    merged.sort(key=lambda p: p.timestamp)

    source: WeatherSource = "live"
    summary = f"Intelligence ({intelligence.weather_source})"

    v2_confidence = _normalize_confidence(intelligence.confidence)

    return SolarForecast(
        site_id=site.site_id,
        generated_at=intelligence.generated_at,
        model_version=MODEL_VERSION,
        quality=_map_quality(intelligence.status, v2_confidence),
        weather_source=source,
        expected_today_kwh=intelligence.expected_today_kwh,
        remaining_today_kwh=intelligence.remaining_today_kwh,
        expected_tomorrow_kwh=intelligence.expected_tomorrow_kwh,
        peak_power_w=intelligence.peak_power_w,
        peak_time=intelligence.peak_time,
        confidence=v2_confidence,
        lower_today_kwh=intelligence.lower_today_kwh,
        upper_today_kwh=intelligence.upper_today_kwh,
        weather_summary=summary,
        points=tuple(merged),
        raw_forecast_today_kwh=intelligence.physical_today_kwh,
    )


async def persist_intelligence_v2_forecast(
    session: AsyncSession,
    record: SolarConfigRecord,
    intelligence: IntelligenceForecast,
    settings: Settings,
    *,
    open_meteo: OpenMeteoWeatherProvider | None = None,
) -> SolarForecast:
    domain = _to_domain_config(record)
    covered_until = max((p.timestamp for p in intelligence.hourly), default=intelligence.generated_at)
    extended: tuple[SolarForecastPoint, ...] = ()
    if open_meteo is not None and settings.solar_forecast_extended_days > 0:
        extended = await build_extended_forecast_points(
            domain,
            open_meteo,
            now=intelligence.generated_at,
            covered_until=covered_until,
            days=settings.solar_forecast_extended_days,
        )

    forecast = compose_solar_forecast(domain, intelligence, extended)
    repo = SolarForecastRepository(session)
    await repo.save_run(forecast)
    logger.info(
        "Persisted v2 bridge forecast site=%s points=%d extended=%d",
        domain.site_id,
        len(forecast.points),
        len(extended),
    )
    return forecast
