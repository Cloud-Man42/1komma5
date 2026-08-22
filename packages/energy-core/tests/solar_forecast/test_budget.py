"""Tests for solar energy budget service."""

from datetime import UTC, datetime, timedelta

from energy_core.solar_forecast.budget import ConsumptionForecast, SolarEnergyBudgetService
from energy_core.solar_forecast.types import SolarForecast, SolarForecastPoint


def _forecast(*, remaining_kwh: float = 12.0) -> SolarForecast:
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    return SolarForecast(
        site_id=1,
        generated_at=now,
        model_version="solar-forecast-v1",
        quality="HIGH",
        weather_source="live",
        expected_today_kwh=remaining_kwh,
        remaining_today_kwh=remaining_kwh,
        expected_tomorrow_kwh=None,
        peak_power_w=5000.0,
        peak_time=now + timedelta(hours=2),
        confidence=0.9,
        lower_today_kwh=remaining_kwh * 0.8,
        upper_today_kwh=remaining_kwh * 1.2,
        weather_summary="Soligt",
        points=(
            SolarForecastPoint(
                timestamp=now,
                baseline_power_w=4000.0,
                corrected_power_w=4000.0,
                expected_energy_kwh=remaining_kwh / 4,
                lower_bound_power_w=3000.0,
                upper_bound_power_w=5000.0,
                confidence=0.9,
            ),
        ),
    )


def test_compute_surplus_when_solar_exceeds_consumption():
    service = SolarEnergyBudgetService()
    budget = service.compute(
        _forecast(remaining_kwh=15.0),
        consumption_forecast=ConsumptionForecast(expected_kwh=8.0),
    )
    assert budget.forecast_solar_kwh == 15.0
    assert budget.expected_house_consumption_kwh == 8.0
    assert budget.expected_surplus_kwh == 7.0
    assert budget.expected_deficit_kwh is None
    assert budget.consumption_source == "historical"


def test_compute_deficit_when_consumption_exceeds_solar():
    service = SolarEnergyBudgetService()
    budget = service.compute(
        _forecast(remaining_kwh=5.0),
        consumption_forecast=ConsumptionForecast(expected_kwh=12.0),
        ev_required_kwh=3.0,
    )
    assert budget.expected_deficit_kwh == 10.0
    assert budget.expected_surplus_kwh is None


def test_compute_without_consumption_marks_unavailable():
    service = SolarEnergyBudgetService()
    budget = service.compute(_forecast())
    assert budget.expected_house_consumption_kwh is None
    assert budget.consumption_source == "unavailable"


def test_compute_battery_available_capacity():
    service = SolarEnergyBudgetService()
    budget = service.compute(
        _forecast(),
        battery_soc_pct=60.0,
        battery_capacity_kwh=10.0,
    )
    assert budget.battery_available_capacity_kwh == 4.0
