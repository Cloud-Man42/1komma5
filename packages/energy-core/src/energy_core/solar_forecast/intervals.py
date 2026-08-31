"""Infer forecast point cadence from timestamps."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.solar_forecast.constants import INTERVAL_HOURS

DEFAULT_HOURLY_INTERVAL_HOURS = 1.0


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def infer_interval_hours_from_timestamps(
    timestamps: list[datetime],
    *,
    default_hours: float = DEFAULT_HOURLY_INTERVAL_HOURS,
) -> float:
    """Return median step length in hours; defaults to 1h when cadence is unknown."""
    if len(timestamps) < 2:
        return default_hours

    ordered = sorted(_as_utc(ts) for ts in timestamps)
    deltas: list[float] = []
    for i in range(1, min(len(ordered), 9)):
        delta_s = (ordered[i] - ordered[i - 1]).total_seconds()
        if delta_s > 0:
            deltas.append(delta_s / 3600.0)
    if not deltas:
        return default_hours

    deltas.sort()
    return deltas[len(deltas) // 2]


def power_to_energy_kwh(power_w: float, interval_hours: float) -> float:
    return (power_w / 1000.0) * interval_hours


def default_v2_interval_hours() -> float:
    """Legacy v2 Open-Meteo minutely_15 cadence."""
    return INTERVAL_HOURS
