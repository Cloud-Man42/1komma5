"""Integration registry tests for Step 4e provider scaffolds."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from energy_core.chargers.framework.catalog import ZAPTEC_REST
from energy_core.chargers.framework.factory import ChargerAdapterFactory, _INTEGRATION_BUILDERS
from energy_core.integrations.tesla.provider import TeslaFleetVehicleProvider, TeslaStubVehicleProvider
from energy_core.integrations.zaptec.adapter import ZaptecRestAdapter
from energy_core.vehicles.provider_factory import _PROVIDER_REGISTRY


def test_zaptec_rest_registered_in_charger_factory() -> None:
    assert ZAPTEC_REST in _INTEGRATION_BUILDERS


def test_tesla_registered_in_vehicle_provider_factory() -> None:
    assert "tesla" in _PROVIDER_REGISTRY


@pytest.mark.asyncio
async def test_zaptec_adapter_uses_mock_client_without_live_credentials():
    charger = SimpleNamespace(
        id=1,
        site_id=2,
        name="Zaptec Go",
        manufacturer="Zaptec",
        model="Go",
        control_source="zaptec_rest",
        manufacturer_id="zaptec",
        model_id="go",
        integration_method=ZAPTEC_REST,
        chargeamp_charger_id=None,
        external_charger_id="installation-1",
        chargeamps_api_key="",
        connection_settings=None,
        bridge_enabled=False,
        min_current_a=6.0,
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    adapter = ChargerAdapterFactory.from_charger_model(charger)
    assert isinstance(adapter, ZaptecRestAdapter)
    result = await adapter.test_connection()
    assert result.success is True
    assert result.status == "MOCK"


@pytest.mark.asyncio
async def test_tesla_mock_provider_returns_vehicle():
    provider = TeslaStubVehicleProvider()
    await provider.connect()
    vehicles = await provider.get_vehicles()
    assert len(vehicles) == 1
    assert vehicles[0].provider == "tesla"
    assert vehicles[0].manufacturer == "Tesla"
    await provider.close()
