"""Historical PV performance queries and anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.constants import (
    ANOMALY_BASELINE_MIN_KWH,
    ANOMALY_RATIO_THRESHOLD,
    INTERVAL_HOURS,
    MIN_COVERAGE_FRACTION,
)
from energy_core.solar_forecast.types import PerformanceSample, WeatherForecastPoint


@dataclass(frozen=True, slots=True)
class ActualBucket:
    bucket_start: datetime
    avg_solar_w: float
    avg_consumption_w: float
    sample_count: int
    expected_samples: int


def floor_15min(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    minute = (ts.minute // 15) * 15
    return ts.replace(minute=minute, second=0, microsecond=0)


def actual_energy_kwh(avg_power_w: float) -> float:
    return (avg_power_w / 1000.0) * INTERVAL_HOURS


def coverage_fraction(bucket: ActualBucket) -> float:
    if bucket.expected_samples <= 0:
        return 0.0
    return min(1.0, bucket.sample_count / bucket.expected_samples)


def irradiance_bucket(irr_wm2: float) -> str:
    if irr_wm2 < 50:
        return "low"
    if irr_wm2 < 200:
        return "medium"
    return "high"


def cloud_bucket(cloud_pct: float | None) -> str:
    if cloud_pct is None:
        return "unknown"
    if cloud_pct < 30:
        return "clear"
    if cloud_pct < 70:
        return "partly"
    return "overcast"


def is_anomaly(
    *,
    actual_kwh: float,
    baseline_kwh: float,
    coverage: float,
    solar_w_near_zero: bool,
) -> bool:
    return (
        coverage < MIN_COVERAGE_FRACTION
        or (
            baseline_kwh >= ANOMALY_BASELINE_MIN_KWH
            and actual_kwh <= baseline_kwh * ANOMALY_RATIO_THRESHOLD
        )
    )


def build_performance_sample(
    *,
    bucket_start: datetime,
    actual_kwh: float,
    baseline_kwh: float,
    weather: WeatherForecastPoint | None,
    coverage: float,
) -> PerformanceSample | None:
    if baseline_kwh <= 0 or coverage < MIN_COVERAGE_FRACTION:
        return None

    ratio = actual_kwh / baseline_kwh if baseline_kwh > 0 else 1.0
    irr = (weather.gti_wm2 or weather.ghi_wm2 or 0.0) if weather else 0.0
    cloud = weather.cloud_cover_pct if weather else None

    anomaly = is_anomaly(
        actual_kwh=actual_kwh,
        baseline_kwh=baseline_kwh,
        coverage=coverage,
        solar_w_near_zero=actual_kwh < 0.001,
    )
    if anomaly:
        return None

    local = bucket_start.astimezone(UTC)
    return PerformanceSample(
        timestamp=bucket_start,
        baseline_energy_kwh=baseline_kwh,
        actual_energy_kwh=actual_kwh,
        performance_ratio=ratio,
        month=local.month,
        hour=local.hour,
        irradiance_bucket=irradiance_bucket(irr),
        cloud_bucket=cloud_bucket(cloud),
        is_anomaly=False,
    )


def recency_weight(age_days: float, month: int, sample_month: int) -> float:
    from energy_core.solar_forecast.constants import RECENCY_WEIGHTS

    base = 0.15
    for max_days, weight in RECENCY_WEIGHTS:
        if age_days <= max_days:
            base = weight
            break

    # Seasonal relevance: same month gets boost
    month_diff = min(abs(month - sample_month), 12 - abs(month - sample_month))
    season_boost = 1.0 + (0.3 if month_diff <= 1 else 0.0)
    return base * season_boost


def aggregate_buckets_from_readings(
    readings: list[tuple[datetime, float, float]],
    bucket_minutes: int = 15,
) -> list[ActualBucket]:
    """Aggregate raw readings (timestamp, solar_w, consumption_w) into buckets."""
    from collections import defaultdict

    buckets: dict[datetime, list[tuple[float, float]]] = defaultdict(list)
    for ts, solar_w, consumption_w in readings:
        key = floor_15min(ts)
        buckets[key].append((solar_w, consumption_w))

    poll_interval_s = 60  # expected ~1 sample/min
    expected = max(1, (bucket_minutes * 60) // poll_interval_s)

    result: list[ActualBucket] = []
    for start in sorted(buckets):
        group = buckets[start]
        n = len(group)
        result.append(
            ActualBucket(
                bucket_start=start,
                avg_solar_w=sum(s for s, _ in group) / n,
                avg_consumption_w=sum(c for _, c in group) / n,
                sample_count=n,
                expected_samples=expected,
            )
        )
    return result


def actual_solar_kwh_today_from_readings(
    readings: list[tuple[datetime, float, float]],
    *,
    timezone: str,
    now: datetime | None = None,
) -> float:
    """Sum measured solar energy (kWh) from local midnight until now."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    tz = ZoneInfo(timezone)
    local_today = now.astimezone(tz).date()
    day_start = datetime.combine(local_today, time.min, tzinfo=tz).astimezone(UTC)

    today_readings = [
        (ts, solar_w, consumption_w)
        for ts, solar_w, consumption_w in readings
        if day_start <= (ts if ts.tzinfo else ts.replace(tzinfo=UTC)) <= now
    ]
    if not today_readings:
        return 0.0

    buckets = aggregate_buckets_from_readings(today_readings)
    return round(
        sum(
            actual_energy_kwh(b.avg_solar_w)
            for b in buckets
            if b.bucket_start.astimezone(tz).date() == local_today
        ),
        3,
    )
