"""Recompute physical baseline for historical days (Phase 0 backfill v0)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.constants import INTERVAL_HOURS
from energy_core.solar_forecast.daily_evaluation import local_day_bounds
from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider
from energy_core.solar_forecast.physical import baseline_energy_kwh, baseline_power_w
from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecastPoint


async def recompute_physical_baseline_kwh_for_day(
    site: SolarSiteConfiguration,
    day: date,
    *,
    provider: OpenMeteoWeatherProvider,
) -> tuple[float, float | None]:
    """Return (physical_kwh, radiation_kwh_m2) using archived weather for a local day."""
    day_start, day_end = local_day_bounds(day, site.timezone)
    forecast = await provider.get_historical(
        site,
        from_ts=day_start,
        to_ts=day_end + timedelta(hours=1),
    )
    tz = ZoneInfo(site.timezone)
    total_kwh = 0.0
    ghi_sum = 0.0
    ghi_count = 0
    for p in forecast.points:
        if p.timestamp.astimezone(tz).date() != day:
            continue
        power = baseline_power_w(p, site)
        total_kwh += baseline_energy_kwh(power)
        if p.ghi_wm2 is not None and p.ghi_wm2 > 0:
            ghi_sum += p.ghi_wm2 * INTERVAL_HOURS / 1000.0
            ghi_count += 1
    radiation_kwh_m2 = round(ghi_sum, 4) if ghi_count else None
    return round(total_kwh, 3), radiation_kwh_m2


def weather_points_for_day(points: list[WeatherForecastPoint], day: date, timezone: str) -> list[WeatherForecastPoint]:
    tz = ZoneInfo(timezone)
    return [p for p in points if p.timestamp.astimezone(tz).date() == day]
