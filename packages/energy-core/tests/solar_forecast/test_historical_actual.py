"""Tests for actual solar production today."""

from datetime import UTC, datetime

from energy_core.solar_forecast.historical import actual_solar_kwh_today_from_readings


def test_actual_solar_kwh_today_sums_buckets():
    tz = "Europe/Stockholm"
    now = datetime(2026, 8, 18, 14, 0, tzinfo=UTC)
    readings = [
        (datetime(2026, 8, 18, 8, 0, tzinfo=UTC), 4000.0, 1000.0),
        (datetime(2026, 8, 18, 8, 5, tzinfo=UTC), 4200.0, 1100.0),
        (datetime(2026, 8, 18, 9, 0, tzinfo=UTC), 5000.0, 1200.0),
        (datetime(2026, 8, 18, 9, 5, tzinfo=UTC), 5200.0, 1300.0),
    ]
    total = actual_solar_kwh_today_from_readings(readings, timezone=tz, now=now)
    assert total > 0


def test_actual_solar_kwh_today_returns_zero_without_readings():
    now = datetime(2026, 8, 18, 14, 0, tzinfo=UTC)
    assert actual_solar_kwh_today_from_readings([], timezone="Europe/Stockholm", now=now) == 0.0


def test_actual_solar_kwh_today_ignores_previous_day():
    tz = "Europe/Stockholm"
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        (datetime(2026, 8, 17, 12, 0, tzinfo=UTC), 6000.0, 1000.0),
        (datetime(2026, 8, 18, 9, 0, tzinfo=UTC), 3000.0, 1000.0),
    ]
    total = actual_solar_kwh_today_from_readings(readings, timezone=tz, now=now)
    assert 0 < total < 1.0
