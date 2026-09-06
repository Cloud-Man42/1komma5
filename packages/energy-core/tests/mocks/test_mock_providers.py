"""Vendor-neutral mock provider tests."""

import pytest

from energy_core.contracts.energy.battery import IBatteryTelemetry
from energy_core.contracts.energy.inverter import IInverterTelemetry
from energy_core.contracts.spa import ISpaControl
from energy_core.mocks.battery import MockBattery
from energy_core.mocks.charger import MockCharger
from energy_core.mocks.inverter import MockInverter
from energy_core.mocks.price_provider import MockPriceProvider
from energy_core.mocks.spa import MockSpa


@pytest.mark.asyncio
async def test_mock_charger_start_stop() -> None:
    charger = MockCharger()
    await charger.start_charging()
    status = await charger.get_status()
    assert status.charging is True
    await charger.stop_charging()
    status = await charger.get_status()
    assert status.charging is False


@pytest.mark.asyncio
async def test_mock_inverter_implements_protocol() -> None:
    inverter = MockInverter()
    assert isinstance(inverter, IInverterTelemetry)
    assert await inverter.get_solar_power_w() == 2500.0


@pytest.mark.asyncio
async def test_mock_battery_implements_protocol() -> None:
    battery = MockBattery()
    assert isinstance(battery, IBatteryTelemetry)
    assert await battery.get_soc_pct() == 80.0


@pytest.mark.asyncio
async def test_mock_price_provider_returns_points() -> None:
    provider = MockPriceProvider()
    points = await provider.fetch(system_id="SE3", from_iso="2026-01-01", to_iso="2026-01-02")
    assert len(points) == 1
    assert points[0].market_price_eur_kwh == 0.12


@pytest.mark.asyncio
async def test_mock_spa_implements_protocol() -> None:
    spa = MockSpa()
    assert isinstance(spa, ISpaControl)
    await spa.set_temperature_c(40.0)
    assert await spa.get_temperature_c() == 40.0
