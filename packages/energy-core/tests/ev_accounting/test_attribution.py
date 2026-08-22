"""Tests for EnergyAttributionEngine (A–E)."""

from energy_core.ev_accounting.attribution import EnergyAttributionEngine
from energy_core.ev_accounting.battery_ledger import BatteryEnergyLedgerService
from energy_core.ev_accounting.models import BatteryLedgerState, SiteEnergySample


def _sample(**kwargs) -> SiteEnergySample:
    defaults = dict(
        pv_power_w=0,
        house_consumption_w=0,
        grid_import_w=0,
        grid_export_w=0,
        battery_charge_w=0,
        battery_discharge_w=0,
        ev_power_w=5000,
        electricity_price_sek_kwh=1.5,
        duration_hours=1.0,
    )
    defaults.update(kwargs)
    return SiteEnergySample(**defaults)


def test_a_pure_solar():
    engine = EnergyAttributionEngine()
    result = engine.attribute_interval(
        5.0,
        _sample(pv_power_w=6000, house_consumption_w=500, grid_export_w=1000),
    )
    assert result.attribution.solar_direct_kwh == 5.0
    assert result.attribution.grid_direct_kwh == 0.0


def test_b_solar_and_grid():
    engine = EnergyAttributionEngine()
    result = engine.attribute_interval(
        5.0,
        _sample(pv_power_w=3000, house_consumption_w=500, grid_import_w=2000),
    )
    assert result.attribution.solar_direct_kwh == 3.0
    assert result.attribution.grid_direct_kwh == 2.0


def test_c_solar_battery():
    ledger = BatteryLedgerState(solar_energy_kwh=10.0, grid_energy_kwh=0.0)
    service = BatteryEnergyLedgerService()
    sample = _sample(battery_discharge_w=4000, pv_power_w=0, house_consumption_w=1000)
    _, split = service._apply_discharge(ledger, 4.0)
    engine = EnergyAttributionEngine()
    result = engine.attribute_interval(4.0, sample, battery_discharge=split)
    assert result.attribution.solar_battery_kwh == 4.0
    assert result.attribution.grid_battery_kwh == 0.0


def test_d_grid_battery():
    ledger = BatteryLedgerState(solar_energy_kwh=0.0, grid_energy_kwh=10.0, grid_energy_cost_sek=5.0)
    service = BatteryEnergyLedgerService()
    _, split = service._apply_discharge(ledger, 4.0)
    engine = EnergyAttributionEngine()
    result = engine.attribute_interval(
        4.0,
        _sample(battery_discharge_w=4000),
        battery_discharge=split,
    )
    assert result.attribution.solar_battery_kwh == 0.0
    assert result.attribution.grid_battery_kwh == 4.0


def test_e_mixed_battery():
    ledger = BatteryLedgerState(solar_energy_kwh=7.0, grid_energy_kwh=3.0, grid_energy_cost_sek=1.5)
    service = BatteryEnergyLedgerService()
    _, split = service._apply_discharge(ledger, 10.0)
    assert round(split.solar_kwh, 1) == 7.0
    assert round(split.grid_kwh, 1) == 3.0
