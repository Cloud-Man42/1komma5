"""Extended multi-day solar forecast beyond the 48h minutely_15 cap."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider
from energy_core.solar_forecast.physical import baseline_power_w
from energy_core.solar_forecast.types import SolarForecastPoint, SolarSiteConfiguration

logger = logging.getLogger(__name__)


async def build_extended_forecast_points(
    site: SolarSiteConfiguration,
    provider: OpenMeteoWeatherProvider,
    *,
    now: datetime,
    covered_until: datetime,
    days: int = 7,
) -> tuple[SolarForecastPoint, ...]:
    """Fetch hourly Open-Meteo data and append points after the near-term horizon."""
    if days <= 0:
        return ()

    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if covered_until.tzinfo is None:
        covered_until = covered_until.replace(tzinfo=UTC)

    try:
        weather = await provider.get_extended_hourly_forecast(site, forecast_days=days)
    except Exception:
        logger.warning("Extended solar forecast fetch failed site=%s", site.site_id, exc_info=True)
        return ()

    points: list[SolarForecastPoint] = []
    for wp in weather.points:
        ts = wp.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts < now or ts <= covered_until:
            continue

        baseline_w = baseline_power_w(wp, site)
        energy = baseline_w / 1000.0
        points.append(
            SolarForecastPoint(
                timestamp=ts,
                baseline_power_w=baseline_w,
                corrected_power_w=baseline_w,
                expected_energy_kwh=energy,
                lower_bound_power_w=baseline_w * 0.85,
                upper_bound_power_w=baseline_w * 1.15,
                confidence=0.4,
                gti_wm2=wp.gti_wm2 or wp.ghi_wm2,
                cloud_cover_pct=wp.cloud_cover_pct,
                correction_factor=1.0,
            )
        )

    return tuple(points)
