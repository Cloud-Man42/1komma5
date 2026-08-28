"""Tests for consumer aggregate helpers."""

from datetime import UTC, datetime
from types import SimpleNamespace

from energy_core.consumer_accounting.aggregator import (
    group_intervals_by_local_period,
    period_bounds,
    quality_percentages,
    spa_cost_split,
    sum_interval_fields,
)


def test_period_bounds_day_stockholm():
    ref = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    start, end = period_bounds(granularity="day", reference=ref, timezone="Europe/Stockholm")
    assert start < end
    assert 23 * 3600 <= (end - start).total_seconds() <= 25 * 3600


def test_quality_percentages():
    pct = quality_percentages({"CALCULATED": 8, "ESTIMATED": 2})
    assert pct["calculated_pct"] == 80.0
    assert pct["estimated_pct"] == 20.0


def test_spa_cost_split():
    totals = {
        "energy_kwh": 2.0,
        "actual_cost_sek": 0.8,
        "reference_cost_sek": 4.0,
        "savings_sek": 3.2,
        "solar_direct_kwh": 0.5,
        "solar_battery_kwh": 0.3,
        "grid_battery_kwh": 0.2,
        "grid_direct_kwh": 1.0,
    }
    costs = spa_cost_split(totals, fallback_price_sek_kwh=2.0)
    assert costs["solar_kwh"] == 0.8
    assert costs["battery_kwh"] == 0.2
    assert costs["grid_kwh"] == 1.0
    assert costs["grid_cost_sek"] == 0.8
    assert costs["solar_value_sek"] == 1.6
    assert costs["battery_value_sek"] == 1.6


def test_sum_interval_fields_empty():
    assert sum_interval_fields([]) == {}


def test_group_intervals_by_local_period_hour():
    hour1 = datetime(2026, 8, 27, 10, 15, tzinfo=UTC)
    hour2 = datetime(2026, 8, 27, 10, 45, tzinfo=UTC)
    hour3 = datetime(2026, 8, 27, 11, 10, tzinfo=UTC)
    intervals = [
        SimpleNamespace(start_time=hour1, energy_kwh=0.5, solar_direct_kwh=0.0, solar_battery_kwh=0.0, grid_battery_kwh=0.0, grid_direct_kwh=0.5, unknown_kwh=0.0, actual_cost_sek=0.5, reference_cost_sek=1.0, savings_sek=0.5, heater_runtime_seconds=0.0, pump_runtime_seconds=0.0, average_power_w=1000.0),
        SimpleNamespace(start_time=hour2, energy_kwh=0.6, solar_direct_kwh=0.0, solar_battery_kwh=0.0, grid_battery_kwh=0.0, grid_direct_kwh=0.6, unknown_kwh=0.0, actual_cost_sek=0.6, reference_cost_sek=1.2, savings_sek=0.6, heater_runtime_seconds=0.0, pump_runtime_seconds=0.0, average_power_w=1200.0),
        SimpleNamespace(start_time=hour3, energy_kwh=0.7, solar_direct_kwh=0.0, solar_battery_kwh=0.0, grid_battery_kwh=0.0, grid_direct_kwh=0.7, unknown_kwh=0.0, actual_cost_sek=0.7, reference_cost_sek=1.4, savings_sek=0.7, heater_runtime_seconds=0.0, pump_runtime_seconds=0.0, average_power_w=1400.0),
    ]
    grouped = group_intervals_by_local_period(intervals, granularity="hour", timezone="Europe/Stockholm")
    assert len(grouped) == 2
    assert grouped[0][1][0].energy_kwh == 0.5
    assert grouped[0][1][1].energy_kwh == 0.6
    assert grouped[1][1][0].energy_kwh == 0.7


def test_group_intervals_by_local_period_day():
    day1 = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)
    day2 = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    intervals = [
        SimpleNamespace(start_time=day1, energy_kwh=1.0, solar_direct_kwh=0.5, solar_battery_kwh=0.0, grid_battery_kwh=0.0, grid_direct_kwh=0.5, unknown_kwh=0.0, actual_cost_sek=1.0, reference_cost_sek=2.0, savings_sek=1.0, heater_runtime_seconds=0.0, pump_runtime_seconds=0.0, average_power_w=1000.0),
        SimpleNamespace(start_time=day2, energy_kwh=2.0, solar_direct_kwh=1.0, solar_battery_kwh=0.0, grid_battery_kwh=0.0, grid_direct_kwh=1.0, unknown_kwh=0.0, actual_cost_sek=2.0, reference_cost_sek=4.0, savings_sek=2.0, heater_runtime_seconds=0.0, pump_runtime_seconds=0.0, average_power_w=2000.0),
    ]
    grouped = group_intervals_by_local_period(intervals, granularity="day", timezone="Europe/Stockholm")
    assert len(grouped) == 2
    assert grouped[0][1][0].energy_kwh == 1.0
    assert grouped[1][1][0].energy_kwh == 2.0
