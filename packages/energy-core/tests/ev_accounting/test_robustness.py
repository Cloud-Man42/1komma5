"""Tests for stale data confidence and session resume (I–J)."""

import pytest
from energy_core.ev_accounting.attribution import EnergyAttributionEngine
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.ev_accounting.session_service import EVSessionService


def test_i_stale_ev_power_lowers_quality():
    engine = EnergyAttributionEngine()
    sample = SiteEnergySample(
        pv_power_w=3000,
        house_consumption_w=500,
        grid_import_w=0,
        grid_export_w=0,
        battery_charge_w=0,
        battery_discharge_w=0,
        ev_power_w=0,
        electricity_price_sek_kwh=1.5,
        duration_hours=1.0,
    )
    result = engine.attribute_interval(2.0, sample, ev_power_w=0)
    assert result.data_quality == "ESTIMATED"
    assert result.confidence <= 0.8


@pytest.mark.asyncio
async def test_j_resume_active_session_state():
    service = EVSessionService()
    state = service.get_runtime_state(42)
    state.last_vehicle_connected = True
    state.last_meter_kwh = 100.0
    assert service.get_runtime_state(42).last_meter_kwh == 100.0
