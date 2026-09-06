"""Tests for Tesla Fleet API integration."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from energy_core.integrations.tesla.client import TeslaApiError, TeslaFleetClient
from energy_core.integrations.tesla.config import build_tesla_connection_info, fleet_api_base_url
from energy_core.integrations.tesla.mock import TeslaMockClient
from energy_core.integrations.tesla.parsing import parse_vehicle_state
from energy_core.integrations.tesla.provider import TeslaFleetVehicleProvider, TeslaStubVehicleProvider


def test_build_tesla_connection_info_defaults_to_mock():
    info = build_tesla_connection_info()
    assert info.mock is True
    assert info.ready is False


def test_fleet_api_base_url_eu_and_na():
    assert "eu" in fleet_api_base_url("Europe")
    assert "na" in fleet_api_base_url("NA")


def test_parse_vehicle_state_from_payload():
    state = parse_vehicle_state(
        {
            "id_s": "vehicle-1",
            "vin": "VIN123",
            "model": "Model Y",
            "charge_state": {"battery_level": 55, "charging_state": "Charging", "charger_power": 7.2},
            "drive_state": {"range": 300},
            "vehicle_state": {"api_version": 70},
        },
        now=datetime(2026, 9, 6, 12, 0, tzinfo=UTC),
    )
    assert state.vehicle_id == "vehicle-1"
    assert state.state_of_charge_percent == 55.0
    assert state.is_charging is True


@pytest.mark.asyncio
async def test_tesla_mock_client_returns_vehicle_state():
    client = TeslaMockClient()
    states = await client.get_vehicle_states()
    assert len(states) == 1
    assert states[0].model == "Model 3"


@pytest.mark.asyncio
async def test_tesla_fleet_provider_exposes_mock_vehicle():
    provider = TeslaFleetVehicleProvider(client=TeslaMockClient(), mock=True)
    await provider.connect()
    vehicles = await provider.get_vehicles()
    assert vehicles[0].provider == "tesla"
    await provider.close()


@pytest.mark.asyncio
async def test_tesla_stub_provider_alias():
    provider = TeslaStubVehicleProvider()
    await provider.connect()
    assert len(await provider.get_vehicles()) == 1
    await provider.close()


@pytest.mark.asyncio
async def test_tesla_fleet_client_auth_failure():
    client = TeslaFleetClient(
        region="Europe",
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
    )
    with patch.object(
        client,
        "_ensure_token",
        AsyncMock(side_effect=TeslaApiError("Tesla auth failed with status 401")),
    ):
        with pytest.raises(TeslaApiError, match="auth failed"):
            await client.list_vehicles()
