"""Tests for historical production day counting."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from energy_core.solar_forecast.historical import count_production_days


def _reading(ts: datetime, solar_w: float) -> tuple[datetime, float, float]:
    return (ts, solar_w, 1000.0)


def test_count_production_days_ignores_empty_days():
    day = date(2026, 6, 14)
    start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
    readings = [_reading(start + timedelta(minutes=i * 15), 4000.0) for i in range(4)]
    now = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    assert count_production_days(readings, timezone="UTC", window_days=3, now=now) == 1


def test_count_production_days_requires_min_kwh():
    day = date(2026, 6, 14)
    start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
    readings = [_reading(start, 100.0)]
    now = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    assert count_production_days(readings, timezone="UTC", window_days=3, now=now, min_kwh=1.0) == 0
