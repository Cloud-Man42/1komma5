"""Tests for power reading kWh integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from energy_core.energy.integration import (
    MAX_INTERVAL_SECONDS,
    integrate_site_energy,
    iter_energy_segments,
)


def _reading(
    recorded_at: datetime,
    *,
    solar_production_w: float | None = 0.0,
    consumption_w: float | None = 0.0,
    grid_import_w: float | None = 0.0,
    grid_export_w: float | None = 0.0,
    battery_power_w: float | None = None,
    battery_charge_w: float | None = None,
    battery_discharge_w: float | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        recorded_at=recorded_at,
        solar_production_w=solar_production_w,
        consumption_w=consumption_w,
        grid_import_w=grid_import_w,
        grid_export_w=grid_export_w,
        battery_power_w=battery_power_w,
        battery_charge_w=battery_charge_w,
        battery_discharge_w=battery_discharge_w,
    )


def test_integrate_single_interval():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, solar_production_w=2000.0, consumption_w=1500.0, grid_import_w=500.0),
        _reading(start + timedelta(minutes=5), solar_production_w=2500.0),
    ]
    totals = integrate_site_energy(readings)
    assert totals.solar_kwh == pytest.approx(2000.0 * (5 / 60) / 1000)
    assert totals.consumption_kwh == pytest.approx(1500.0 * (5 / 60) / 1000)
    assert totals.import_kwh == pytest.approx(500.0 * (5 / 60) / 1000)
    assert totals.export_kwh == 0.0


def test_integrate_sums_multiple_intervals():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, solar_production_w=1000.0),
        _reading(start + timedelta(minutes=5), solar_production_w=2000.0),
        _reading(start + timedelta(minutes=10), solar_production_w=3000.0),
    ]
    totals = integrate_site_energy(readings)
    expected = (1000.0 + 2000.0) * (5 / 60) / 1000
    assert totals.solar_kwh == pytest.approx(expected)


def test_skips_non_positive_interval():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, solar_production_w=1000.0),
        _reading(start, solar_production_w=2000.0),
        _reading(start + timedelta(minutes=5), solar_production_w=3000.0),
    ]
    totals = integrate_site_energy(readings)
    assert totals.solar_kwh == pytest.approx(2000.0 * (5 / 60) / 1000)


def test_skips_intervals_over_cap():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, solar_production_w=1000.0),
        _reading(start + timedelta(seconds=MAX_INTERVAL_SECONDS + 1), solar_production_w=2000.0),
    ]
    totals = integrate_site_energy(readings)
    assert totals.solar_kwh == 0.0


def test_clamps_negative_power_to_zero():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, solar_production_w=-500.0, grid_export_w=-100.0),
        _reading(start + timedelta(minutes=5)),
    ]
    totals = integrate_site_energy(readings)
    assert totals.solar_kwh == 0.0
    assert totals.export_kwh == 0.0


def test_naive_timestamps_treated_as_utc():
    start = datetime(2026, 8, 18, 10, 0)
    readings = [
        _reading(start, solar_production_w=1000.0),
        _reading(start + timedelta(minutes=5), solar_production_w=2000.0),
    ]
    segments = list(iter_energy_segments(readings))
    assert len(segments) == 1
    assert segments[0].started_at.tzinfo == UTC


def test_battery_from_signed_power_when_channels_missing():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, battery_power_w=1200.0),
        _reading(start + timedelta(minutes=5), battery_power_w=800.0),
        _reading(start + timedelta(minutes=10), battery_power_w=-600.0),
        _reading(start + timedelta(minutes=15), battery_power_w=-400.0),
    ]
    totals = integrate_site_energy(readings, include_battery=True)
    assert totals.battery_charged_kwh == pytest.approx((1200.0 + 800.0) * (5 / 60) / 1000)
    assert totals.battery_discharged_kwh == pytest.approx(600.0 * (5 / 60) / 1000)


def test_battery_channels_take_precedence_over_signed_power():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(
            start,
            battery_power_w=500.0,
            battery_charge_w=900.0,
            battery_discharge_w=100.0,
        ),
        _reading(start + timedelta(minutes=5)),
    ]
    totals = integrate_site_energy(readings, include_battery=True)
    assert totals.battery_charged_kwh == pytest.approx(900.0 * (5 / 60) / 1000)
    assert totals.battery_discharged_kwh == pytest.approx(100.0 * (5 / 60) / 1000)


def test_battery_excluded_by_default():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    readings = [
        _reading(start, battery_power_w=1200.0),
        _reading(start + timedelta(minutes=5)),
    ]
    totals = integrate_site_energy(readings)
    assert totals.battery_charged_kwh == 0.0
    assert totals.battery_discharged_kwh == 0.0


def test_empty_or_single_reading_yields_zero_totals():
    start = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    assert integrate_site_energy([]) == integrate_site_energy([])
    assert integrate_site_energy([_reading(start, solar_production_w=1000.0)]).solar_kwh == 0.0
