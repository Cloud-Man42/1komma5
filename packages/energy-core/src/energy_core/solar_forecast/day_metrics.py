"""Recompute intraday solar forecast metrics from stored forecast points."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.types import SolarForecast, SolarForecastPoint
from energy_core.solar_forecast.physical import baseline_energy_kwh


@dataclass(frozen=True)
class SolarDayMetrics:
    expected_today_kwh: float
    forecast_so_far_kwh: float
    remaining_today_kwh: float
    peak_power_w: float
    peak_time: datetime | None
    raw_forecast_so_far_kwh: float = 0.0
    raw_expected_today_kwh: float = 0.0


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


def tomorrow_forecast_points(
    points: tuple[SolarForecastPoint, ...] | list[SolarForecastPoint],
    *,
    timezone: str,
    now: datetime | None = None,
) -> list[SolarForecastPoint]:
    when = _as_utc(now or datetime.now(UTC))
    tz = ZoneInfo(timezone)
    local_tomorrow = when.astimezone(tz).date() + timedelta(days=1)
    return [p for p in points if _local_date(p.timestamp, tz) == local_tomorrow]


def compute_tomorrow_kwh(
    forecast: SolarForecast,
    *,
    timezone: str,
    now: datetime | None = None,
) -> float | None:
    """Sum expected energy for calendar tomorrow from stored forecast points."""
    pts = tomorrow_forecast_points(forecast.points, timezone=timezone, now=now)
    if not pts:
        return None
    return round(sum(p.expected_energy_kwh for p in pts), 3)


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
        raw_total = float(getattr(forecast, "raw_forecast_today_kwh", 0.0) or 0.0)
        return SolarDayMetrics(
            expected_today_kwh=float(forecast.expected_today_kwh or 0.0),
            forecast_so_far_kwh=max(
                0.0,
                float(forecast.expected_today_kwh or 0.0) - float(forecast.remaining_today_kwh or 0.0),
            ),
            remaining_today_kwh=float(forecast.remaining_today_kwh or 0.0),
            peak_power_w=float(forecast.peak_power_w or 0.0),
            peak_time=forecast.peak_time,
            raw_forecast_so_far_kwh=0.0,
            raw_expected_today_kwh=raw_total,
        )

    past = [p for p in today_pts if _as_utc(p.timestamp) <= when]
    future = [p for p in today_pts if _as_utc(p.timestamp) > when]

    forecast_so_far = sum(p.expected_energy_kwh for p in past)
    remaining = sum(p.expected_energy_kwh for p in future)
    expected = forecast_so_far + remaining
    raw_so_far = sum(baseline_energy_kwh(p.baseline_power_w) for p in past)
    raw_total = sum(baseline_energy_kwh(p.baseline_power_w) for p in today_pts)

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
        raw_forecast_so_far_kwh=round(raw_so_far, 3),
        raw_expected_today_kwh=round(raw_total, 3),
    )
