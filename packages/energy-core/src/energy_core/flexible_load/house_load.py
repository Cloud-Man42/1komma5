"""Hourly house load forecast from historical readings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class HourlyLoadForecast:
    timestamp: datetime
    expected_power_w: float
    confidence: float


@dataclass(frozen=True, slots=True)
class HouseLoadForecastSeries:
    points: tuple[HourlyLoadForecast, ...]
    source: str
    confidence: float


class HouseLoadForecastProvider:
    """Build hour-of-day consumption profile from trailing readings."""

    MIN_SAMPLES = 48
    LOOKBACK_DAYS = 14

    def forecast_series(
        self,
        readings: list[tuple[datetime, float | None, float | None]],
        *,
        timezone: str,
        start: datetime,
        end: datetime,
        interval_minutes: int = 15,
    ) -> HouseLoadForecastSeries:
        if len(readings) < self.MIN_SAMPLES:
            flat = self._flat_mean(readings)
            return self._flat_series(start, end, flat, interval_minutes, confidence=0.2)

        tz = ZoneInfo(timezone)
        weekday_profile, weekend_profile, overall = self._build_profiles(readings, tz)
        points: list[HourlyLoadForecast] = []
        cursor = start
        step = timedelta(minutes=interval_minutes)
        while cursor < end:
            local = cursor.astimezone(tz)
            is_weekend = local.weekday() >= 5
            profile = weekend_profile if is_weekend else weekday_profile
            power = profile.get(local.hour, overall)
            confidence = 0.7 if profile else 0.4
            points.append(HourlyLoadForecast(timestamp=cursor, expected_power_w=power, confidence=confidence))
            cursor += step

        avg_conf = mean(p.confidence for p in points) if points else 0.3
        return HouseLoadForecastSeries(points=tuple(points), source="historical", confidence=avg_conf)

    def _build_profiles(
        self,
        readings: list[tuple[datetime, float | None, float | None]],
        tz: ZoneInfo,
    ) -> tuple[dict[int, float], dict[int, float], float]:
        weekday: dict[int, list[float]] = {}
        weekend: dict[int, list[float]] = {}
        all_vals: list[float] = []
        cutoff = datetime.now(UTC) - timedelta(days=self.LOOKBACK_DAYS)

        for ts, _solar, consumption in readings:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff:
                continue
            if consumption is None or consumption < 0:
                continue
            local = ts.astimezone(tz)
            all_vals.append(consumption)
            bucket = weekend if local.weekday() >= 5 else weekday
            bucket.setdefault(local.hour, []).append(consumption)

        weekday_profile = {h: mean(vals) for h, vals in weekday.items()}
        weekend_profile = {h: mean(vals) for h, vals in weekend.items()}
        overall = mean(all_vals) if all_vals else 500.0
        return weekday_profile, weekend_profile, overall

    def _flat_mean(self, readings: list[tuple[datetime, float | None, float | None]]) -> float:
        vals = [c for _, _, c in readings if c is not None and c >= 0]
        return mean(vals) if vals else 500.0

    def _flat_series(
        self,
        start: datetime,
        end: datetime,
        power_w: float,
        interval_minutes: int,
        *,
        confidence: float,
    ) -> HouseLoadForecastSeries:
        points: list[HourlyLoadForecast] = []
        cursor = start
        step = timedelta(minutes=interval_minutes)
        while cursor < end:
            points.append(HourlyLoadForecast(timestamp=cursor, expected_power_w=power_w, confidence=confidence))
            cursor += step
        return HouseLoadForecastSeries(points=tuple(points), source="flat_mean", confidence=confidence)
