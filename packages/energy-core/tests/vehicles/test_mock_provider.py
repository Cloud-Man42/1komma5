"""Tests for MockVehicleProvider scenarios."""

import pytest

from energy_core.vehicles.abstractions.models import DataQuality, VehicleConnectionState
from energy_core.vehicles.mock.provider import MockVehicleProvider, MockVehicleScenario


@pytest.mark.asyncio
async def test_connected_idle_scenario():
    provider = MockVehicleProvider(scenario=MockVehicleScenario.CONNECTED_IDLE)
    await provider.connect()
    vehicles = await provider.get_vehicles()
    assert len(vehicles) == 1
    assert vehicles[0].state_of_charge_percent == 34.0
    assert vehicles[0].connection_state == VehicleConnectionState.CONNECTED


@pytest.mark.asyncio
async def test_charging_ramp_increases_power_and_soc():
    provider = MockVehicleProvider(scenario=MockVehicleScenario.CHARGING_RAMP, tick_seconds=0.01)
    await provider.connect()
    events = []
    async for event in provider.watch_vehicle_state():
        events.append(event)
        if len(events) >= 3:
            break
    await provider.close()
    assert events[0].state.charging_power_kw == 3.7
    assert events[-1].state.charging_power_kw == 11.0
    assert events[-1].state.state_of_charge_percent == 44.0


@pytest.mark.asyncio
async def test_backend_unavailable_fails_on_connect():
    provider = MockVehicleProvider(scenario=MockVehicleScenario.BACKEND_UNAVAILABLE)
    with pytest.raises(RuntimeError, match="unavailable"):
        await provider.connect()


@pytest.mark.asyncio
async def test_stale_telemetry_marks_data_quality():
    provider = MockVehicleProvider(scenario=MockVehicleScenario.STALE_TELEMETRY)
    await provider.connect()
    vehicles = await provider.get_vehicles()
    assert vehicles[0].data_quality == DataQuality.STALE
    assert vehicles[0].connection_state == VehicleConnectionState.DEGRADED


@pytest.mark.asyncio
async def test_websocket_disconnect_moves_to_reconnecting():
    provider = MockVehicleProvider(scenario=MockVehicleScenario.WEBSOCKET_DISCONNECT, tick_seconds=0.01)
    await provider.connect()
    events = []
    async for event in provider.watch_vehicle_state():
        events.append(event)
        if len(events) >= 2:
            break
    await provider.close()
    assert events[-1].state.connection_state == VehicleConnectionState.RECONNECTING
