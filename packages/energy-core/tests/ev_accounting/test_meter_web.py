"""Tests for ChargeAmpsMeterAdapter web parsing."""

from unittest.mock import AsyncMock, patch

import pytest

from energy_core.chargers.charge_amps_web import ChargeAmpsWebController
from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter


@pytest.mark.asyncio
async def test_web_meter_snapshot_parses_cumulative_kwh():
    controller = ChargeAmpsWebController("2106037142M", email="u@example.com", password="secret", use_mock=False)
    payload = {
        "ip": "1.2.3.4",
        "connectors": [
            {
                "connectorId": 1,
                "totalConsumptionKwh": 42.5,
                "current1": 8.0,
                "current2": 8.0,
                "current3": 8.0,
                "isCharging": True,
                "ocppStatus": "Charging",
            }
        ],
    }
    adapter = ChargeAmpsMeterAdapter("2106037142M", web_controller=controller)
    with patch.object(controller, "_request", AsyncMock(return_value=payload)):
        snapshot = await adapter.get_snapshot()
    assert snapshot.cumulative_kwh == 42.5
    assert snapshot.is_charging is True
    assert snapshot.energy_source == "meter"
    assert snapshot.power_w == pytest.approx(5520.0)


@pytest.mark.asyncio
async def test_web_meter_detects_preparing_as_vehicle_connected():
    controller = ChargeAmpsWebController("2106037142M", email="u@example.com", password="secret", use_mock=False)
    payload = {
        "ip": "1.2.3.4",
        "connectors": [
            {
                "connectorId": 1,
                "isCharging": False,
                "ocppStatus": "Preparing",
            }
        ],
    }
    adapter = ChargeAmpsMeterAdapter("2106037142M", web_controller=controller)
    with patch.object(controller, "_request", AsyncMock(return_value=payload)):
        snapshot = await adapter.get_snapshot()
    assert snapshot.vehicle_connected is True
    assert snapshot.is_charging is False


@pytest.mark.asyncio
async def test_meter_build_prefers_web_when_credentials_exist(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "secret")
    adapter = ChargeAmpsMeterAdapter.build("2106037142M", api_key="external-key")
    assert adapter._web is not None
    assert adapter._external is None
