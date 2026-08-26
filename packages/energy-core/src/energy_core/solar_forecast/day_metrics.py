"""Recompute intraday solar forecast metrics from stored forecast points."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.types import SolarForecast, SolarForecastPoint


@dataclass(frozen=True)
class SolarDayMetrics:
    expected_today_kwh: float
    forecast_so_far_kwh: float
    remaining_today_kwh: float
    peak_power_w: float
    peak_time: datetime | None


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _local_date(ts: datetime, tz: ZoneInfo):
    return _as_utc(ts).astimezone(tz).date()


def today_forecast_points(
    points: tuple[SolarForecastPoint, ...] | list[SolarForecastPoint],
    *,
    timezone: str,
    now: datetime | None = None,
) -> list[SolarForecastPoint]:
    when = _as_utc(now or datetime.now(UTC))
    tz = ZoneInfo(timezone)
    local_today = when.astimezone(tz).date()
    return [p for p in points if _local_date(p.timestamp, tz) == local_today]


def compute_solar_day_metrics(
    forecast: SolarForecast,
    *,
    timezone: str,
    now: datetime | None = None,
) -> SolarDayMetrics:
    """Split today's forecast curve into elapsed vs remaining energy at ``now``."""
    when = _as_utc(now or datetime.now(UTC))

    today_pts = today_forecast_points(forecast.points, timezone=timezone, now=when)
    if not today_pts:
        return SolarDayMetrics(
            expected_today_kwh=float(forecast.expected_today_kwh or 0.0),
            forecast_so_far_kwh=max(
                0.0,
                float(forecast.expected_today_kwh or 0.0) - float(forecast.remaining_today_kwh or 0.0),
            ),
            remaining_today_kwh=float(forecast.remaining_today_kwh or 0.0),
            peak_power_w=float(forecast.peak_power_w or 0.0),
            peak_time=forecast.peak_time,
        )

    past = [p for p in today_pts if _as_utc(p.timestamp) <= when]
    future = [p for p in today_pts if _as_utc(p.timestamp) > when]

    forecast_so_far = sum(p.expected_energy_kwh for p in past)
    remaining = sum(p.expected_energy_kwh for p in future)
    expected = forecast_so_far + remaining

    peak_w = 0.0
    peak_time: datetime | None = None
    for point in today_pts:
        if point.corrected_power_w > peak_w:
            peak_w = point.corrected_power_w
            peak_time = point.timestamp

    return SolarDayMetrics(
        expected_today_kwh=round(expected, 3),
        forecast_so_far_kwh=round(forecast_so_far, 3),
        remaining_today_kwh=round(remaining, 3),
        peak_power_w=peak_w,
        peak_time=peak_time,
    )
