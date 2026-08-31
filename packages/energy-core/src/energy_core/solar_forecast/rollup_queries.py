"""Solar analysis helpers backed by energy_hourly / energy_daily rollups."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from energy_core.db.repositories import DailyRollup, EnergyReadingRepository, HourlyRollup
from energy_core.solar_forecast.daily_evaluation import actual_kwh_for_day, local_day_bounds
from energy_core.solar_forecast.historical import (
    ActualBucket,
    actual_solar_kwh_today_from_readings,
    aggregate_buckets_from_readings,
    count_production_days,
)


def hourly_to_readings(hourly: list[HourlyRollup]) -> list[tuple[datetime, float, float]]:
    """Convert hourly kWh rollups to pseudo-readings for legacy solar helpers."""
    result: list[tuple[datetime, float, float]] = []
    for row in hourly:
        ts = row.hour if row.hour.tzinfo else row.hour.replace(tzinfo=UTC)
        result.append((ts, row.solar_kwh * 1000.0, row.consumption_kwh * 1000.0))
    return result


def hourly_to_buckets(hourly: list[HourlyRollup]) -> list[ActualBucket]:
    """Convert hourly rollups to performance sample buckets."""
    buckets: list[ActualBucket] = []
    for row in hourly:
        ts = row.hour if row.hour.tzinfo else row.hour.replace(tzinfo=UTC)
        buckets.append(
            ActualBucket(
                bucket_start=ts,
                avg_solar_w=row.solar_kwh * 1000.0,
                avg_consumption_w=row.consumption_kwh * 1000.0,
                sample_count=60,
                expected_samples=60,
            )
        )
    return buckets


def actual_kwh_from_daily(daily: DailyRollup | None) -> tuple[float, float]:
    if daily is None:
        return 0.0, 0.0
    return round(daily.solar_kwh, 3), 100.0


async def actual_solar_kwh_today(
    repo: EnergyReadingRepository,
    site_id: int,
    *,
    timezone: str,
    now: datetime | None = None,
) -> float:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    tz = ZoneInfo(timezone)
    local_today = now.astimezone(tz).date()

    daily = await repo.get_daily_rollup(site_id, local_today)
    if daily is not None:
        return round(daily.solar_kwh, 3)

    day_start = datetime.combine(local_today, time.min, tzinfo=tz).astimezone(UTC)
    hourly = await repo.list_hourly_rollups(site_id, from_time=day_start, to_time=now)
    if hourly:
        return round(sum(row.solar_kwh for row in hourly), 3)

    readings = await repo.list_readings(site_id, from_time=day_start, to_time=now, limit=5000)
    raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]
    return actual_solar_kwh_today_from_readings(raw, timezone=timezone, now=now)


async def count_production_days_observed(
    repo: EnergyReadingRepository,
    site_id: int,
    *,
    timezone: str,
    window_days: int,
    now: datetime | None = None,
    min_kwh: float = 1.0,
) -> int:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    tz = ZoneInfo(timezone)
    local_today = now.astimezone(tz).date()
    from_day = local_today - timedelta(days=window_days + 2)
    daily = await repo.list_daily_rollups(site_id, from_day=from_day, to_day=local_today - timedelta(days=1))
    if daily:
        return sum(1 for row in daily if row.solar_kwh >= min_kwh)

    since = now - timedelta(days=window_days + 2)
    readings = await repo.list_readings(site_id, from_time=since, to_time=now, limit=10000)
    raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]
    return count_production_days(raw, timezone=timezone, window_days=window_days, now=now, min_kwh=min_kwh)


async def actual_kwh_for_day_resolved(
    repo: EnergyReadingRepository,
    site_id: int,
    day: date,
    *,
    timezone: str,
) -> tuple[float, float]:
    daily = await repo.get_daily_rollup(site_id, day)
    if daily is not None:
        return actual_kwh_from_daily(daily)

    day_start, day_end = local_day_bounds(day, timezone)
    hourly = await repo.list_hourly_rollups(site_id, from_time=day_start, to_time=day_end)
    if hourly:
        actual = round(sum(row.solar_kwh for row in hourly), 3)
        return actual, 100.0

    readings = await repo.list_readings(site_id, from_time=day_start, to_time=day_end, limit=5000)
    raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]
    return actual_kwh_for_day(raw, day, timezone)


async def load_consumption_profile_readings(
    repo: EnergyReadingRepository,
    site_id: int,
    *,
    days: int,
    now: datetime | None = None,
) -> list[tuple[datetime, float, float]]:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)
    hourly = await repo.list_hourly_rollups(site_id, from_time=since, to_time=now)
    if len(hourly) >= 48:
        return hourly_to_readings(hourly)

    readings = await repo.list_readings(site_id, from_time=since, to_time=now, limit=10000)
    return [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]


async def load_performance_sample_buckets(
    repo: EnergyReadingRepository,
    site_id: int,
    *,
    days: int,
    now: datetime | None = None,
) -> list[ActualBucket]:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)
    hourly = await repo.list_hourly_rollups(site_id, from_time=since, to_time=now)
    if hourly:
        return hourly_to_buckets(hourly)

    readings = await repo.list_readings(site_id, from_time=since, to_time=now, limit=10000)
    raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]
    return aggregate_buckets_from_readings(raw)


async def daily_actuals_for_range(
    repo: EnergyReadingRepository,
    site_id: int,
    *,
    from_day: date,
    to_day: date,
    timezone: str,
) -> dict[date, tuple[float, float]]:
    daily_rows = await repo.list_daily_rollups(site_id, from_day=from_day, to_day=to_day)
    result = {row.day: actual_kwh_from_daily(row) for row in daily_rows}

    missing = [
        day
        for day in (
            from_day + timedelta(days=offset)
            for offset in range((to_day - from_day).days + 1)
        )
        if day not in result
    ]
    for day in missing:
        result[day] = await actual_kwh_for_day_resolved(repo, site_id, day, timezone=timezone)
    return result
