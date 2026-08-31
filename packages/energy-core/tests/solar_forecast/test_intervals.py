"""Tests for forecast interval inference."""

from __future__ import annotations

from datetime import datetime, timezone

from energy_core.solar_forecast.intervals import (
    infer_interval_hours_from_timestamps,
    power_to_energy_kwh,
)


def test_infer_interval_hours_defaults_to_one_for_single_point():
    ts = datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc)
    assert infer_interval_hours_from_timestamps([ts]) == 1.0


def test_infer_interval_hours_detects_hourly_cadence():
    base = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    stamps = [base.replace(hour=8 + i) for i in range(4)]
    assert infer_interval_hours_from_timestamps(stamps) == 1.0


def test_infer_interval_hours_detects_fifteen_minute_cadence():
    base = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    stamps = [base.replace(minute=i * 15) for i in range(4)]
    assert infer_interval_hours_from_timestamps(stamps) == 0.25


def test_power_to_energy_kwh():
    assert power_to_energy_kwh(2000.0, 1.0) == 2.0
    assert power_to_energy_kwh(2000.0, 0.25) == 0.5
