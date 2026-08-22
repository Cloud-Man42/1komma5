"""Tests for EVChargingCostCalculator (F–G)."""

from energy_core.ev_accounting.cost import EVChargingCostCalculator
from energy_core.ev_accounting.models import EnergyAttribution


def test_f_grid_direct_cost():
    calc = EVChargingCostCalculator()
    result = calc.interval_costs(
        EnergyAttribution(grid_direct_kwh=5.0),
        grid_price_sek_kwh=1.5,
        grid_battery_avg_cost_sek_kwh=None,
        export_compensation_sek_kwh=0.8,
    )
    assert result.actual_cash_cost_sek == 7.5


def test_g_battery_grid_cost():
    calc = EVChargingCostCalculator()
    result = calc.interval_costs(
        EnergyAttribution(grid_battery_kwh=5.0),
        grid_price_sek_kwh=1.5,
        grid_battery_avg_cost_sek_kwh=0.5,
        export_compensation_sek_kwh=0.8,
    )
    assert result.actual_cash_cost_sek == 2.5
