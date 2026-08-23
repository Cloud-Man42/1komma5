"""Tests for Charge Amps adapters."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.charge_amps import (
    ChargeAmpsExternalController,
    ChargeAmpsHaloController,
    build_chargeamps_controller,
)
from energy_core.chargers.charge_amps_web import ChargeAmpsWebController, _valid_rfid_tag
from energy_core.chargers.mock import MockChargeAmpsController


@pytest.mark.asyncio
async def test_mock_set_current_limit():
    controller = MockChargeAmpsController("test-charger")
    await controller.set_current_limit(10.0)
    status = await controller.get_status()
    assert status.current_limit_a == 10.0
    assert status.charging is True


@pytest.mark.asyncio
async def test_mock_stop_charging():
    controller = MockChargeAmpsController("test-charger")
    await controller.set_current_limit(10.0)
    await controller.stop_charging()
    status = await controller.get_status()
    assert status.current_limit_a == 0.0
    assert status.charging is False


@pytest.mark.asyncio
async def test_halo_disconnected_mock():
    controller = MockChargeAmpsController("test-charger", connected=False)
    assert await controller.is_connected() is False


@pytest.mark.asyncio
async def test_chargeamps_defaults_to_mock_without_api_key():
    controller = ChargeAmpsHaloController("halo-1", use_mock=True)
    await controller.set_current_limit(8.0)
    status = await controller.get_status()
    assert status.current_limit_a == 8.0


@pytest.mark.asyncio
async def test_build_chargeamps_controller_uses_web_provider(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_PROVIDER", "web")
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "secret")
    monkeypatch.delenv("CHARGEAMPS_API_KEY", raising=False)

    controller = build_chargeamps_controller("2106037142M", use_mock=False)
    assert isinstance(controller, ChargeAmpsWebController)


@pytest.mark.asyncio
async def test_build_chargeamps_controller_prefers_external_when_charger_api_key_present(
    monkeypatch,
):
    monkeypatch.setenv("CHARGEAMPS_PROVIDER", "web")
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "secret")
    monkeypatch.delenv("CHARGEAMPS_API_KEY", raising=False)

    controller = build_chargeamps_controller(
        "2106037142M",
        api_key="charger-key",
        use_mock=False,
    )
    assert isinstance(controller, ChargeAmpsExternalController)


@pytest.mark.asyncio
async def test_build_chargeamps_controller_uses_external_when_api_key_present(monkeypatch):
    monkeypatch.delenv("CHARGEAMPS_PROVIDER", raising=False)
    monkeypatch.setenv("CHARGEAMPS_API_KEY", "valid-key")

    controller = build_chargeamps_controller("2106037142M", use_mock=False)
    assert isinstance(controller, ChargeAmpsExternalController)


@pytest.mark.asyncio
async def test_web_get_status_parses_connector():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    payload = {
        "ip": "80.208.66.224",
        "connectors": [
            {
                "connectorId": 1,
                "userCurrent": 12.0,
                "isCharging": True,
                "ocppStatus": "Charging",
                "defaultNfcTagId": "123456",
            }
        ],
    }
    with patch.object(controller, "_request", AsyncMock(return_value=payload)):
        status = await controller.get_status()

    assert status.connected is True
    assert status.charging is True
    assert status.current_limit_a == 12.0
    assert status.vehicle_connected is True
    assert controller._default_rfid_tag == "123456"


@pytest.mark.asyncio
async def test_web_get_status_ignores_placeholder_default_nfc_tag():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    payload = {
        "ip": "80.208.66.224",
        "connectors": [
            {
                "connectorId": 1,
                "userCurrent": 16.0,
                "isCharging": False,
                "ocppStatus": "Available",
                "defaultNfcTagId": "00000000000000",
            }
        ],
    }
    with patch.object(controller, "_request", AsyncMock(return_value=payload)):
        status = await controller.get_status()

    assert controller._default_rfid_tag is None
    assert status.vehicle_connected is False
    assert status.charging is False


@pytest.mark.asyncio
async def test_web_get_status_preparing_means_vehicle_connected():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    payload = {
        "ip": "80.208.66.224",
        "connectors": [
            {
                "connectorId": 1,
                "userCurrent": 16.0,
                "isCharging": False,
                "ocppStatus": "Preparing",
            }
        ],
    }
    with patch.object(controller, "_request", AsyncMock(return_value=payload)):
        status = await controller.get_status()

    assert status.vehicle_connected is True
    assert status.charging is False


@pytest.mark.asyncio
async def test_web_set_current_limit_calls_updateusersettings():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    request = AsyncMock(return_value={})
    with patch.object(controller, "_request", request):
        await controller.set_current_limit(10.0)

    request.assert_awaited_once_with(
        "PUT",
        "/chargepoints/2106037142M/updateusersettings",
        params={"userCurrentConnector1": 10},
    )


@pytest.mark.asyncio
async def test_web_start_charging_uses_default_rfid_tag():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    request = AsyncMock(return_value={})
    controller._default_rfid_tag = "654321"
    idle_status = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        current_limit_a=16.0,
        charging=False,
    )
    with (
        patch.object(controller, "get_status", AsyncMock(return_value=idle_status)),
        patch.object(controller, "_request", request),
    ):
        await controller.start_charging()

    request.assert_awaited_once_with(
        "PUT",
        "/chargepoints/2106037142M/1/remotestart",
        params={"rfidTag": "654321"},
    )


@pytest.mark.asyncio
async def test_web_start_charging_skips_remotestart_when_already_charging():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    request = AsyncMock(return_value={})
    charging_status = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        current_limit_a=16.0,
        charging=True,
    )
    with (
        patch.object(controller, "get_status", AsyncMock(return_value=charging_status)),
        patch.object(controller, "_request", request),
    ):
        await controller.start_charging()

    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_web_start_charging_fetches_rfid_when_default_is_placeholder():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    request_json = AsyncMock(
        side_effect=[
            [{"id": "0474F0F2636B81", "active": True}],
        ]
    )
    request = AsyncMock(return_value={})
    idle_status = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        current_limit_a=16.0,
        charging=False,
    )
    with (
        patch.object(controller, "get_status", AsyncMock(return_value=idle_status)),
        patch.object(controller, "_request_json", request_json),
        patch.object(controller, "_request", request),
    ):
        await controller.start_charging()

    request_json.assert_awaited_once_with(
        "GET",
        "/chargepoints/2106037142M/1/remotestart/tags",
    )
    request.assert_awaited_once_with(
        "PUT",
        "/chargepoints/2106037142M/1/remotestart",
        params={"rfidTag": "0474F0F2636B81"},
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00000000000000", None),
        ("0474F0F2636B81", "0474F0F2636B81"),
        ("654321", "654321"),
        ("", None),
        (None, None),
    ],
)
def test_valid_rfid_tag_rejects_placeholder(value, expected):
    assert _valid_rfid_tag(value) == expected


@pytest.mark.asyncio
async def test_web_stop_charging_sets_zero_current_without_remotestop_when_idle():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    request = AsyncMock(
        return_value={
            "ip": "80.208.66.224",
            "connectors": [
                {
                    "connectorId": 1,
                    "isCharging": False,
                    "ocppStatus": "Available",
                    "userCurrent": 16.0,
                }
            ],
        }
    )
    with patch.object(controller, "_request", request):
        await controller.stop_charging()

    assert request.await_count == 2
    assert request.await_args_list[0].args == ("GET", "/chargepoints/2106037142M")
    assert request.await_args_list[1].kwargs["params"] == {"userCurrentConnector1": 0}


@pytest.mark.asyncio
async def test_web_login_failure_raises():
    controller = ChargeAmpsWebController(
        "2106037142M", email="user@example.com", password="secret", use_mock=False
    )
    response = httpx.Response(
        401, request=httpx.Request("POST", "https://my.charge.space/api/auth/login")
    )
    with patch(
        "energy_core.chargers.charge_amps_web.httpx.AsyncClient",
    ) as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "unauthorized", request=response.request, response=response
            )
        )
        client_cls.return_value = client

        with pytest.raises(httpx.HTTPStatusError):
            await controller._ensure_token()


@pytest.mark.asyncio
async def test_external_controller_uses_web_vehicle_status_fallback(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "secret")
    controller = ChargeAmpsExternalController(
        "2106037142M",
        api_key="valid-key",
        use_mock=False,
    )
    external_status = ChargerStatus(
        connected=True,
        vehicle_connected=False,
        current_limit_a=16.0,
        charging=False,
    )
    web_status = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        current_limit_a=16.0,
        charging=False,
    )
    with (
        patch.object(controller._adapter, "get_status", AsyncMock(return_value=external_status)),
        patch.object(
            controller._web_status,
            "get_status",
            AsyncMock(return_value=web_status),
        ),
    ):
        status = await controller.get_status()
    assert status.vehicle_connected is True


@pytest.mark.asyncio
async def test_external_get_status_parses_v5_response():
    controller = ChargeAmpsExternalController(
        "2106037142M",
        api_key="valid-key",
        email="user@example.com",
        password="secret",
        use_mock=False,
    )
    status_payload = {
        "connectorStatuses": [
            {"connectorId": 1, "status": "Charging"},
        ]
    }
    settings_payload = {
        "chargePointId": "2106037142M",
        "connectorId": 1,
        "mode": "On",
        "rfidLock": False,
        "cableLock": False,
        "maxCurrent": 16.0,
    }
    with patch.object(
        controller._adapter._client,
        "_request",
        AsyncMock(side_effect=[status_payload, settings_payload]),
    ):
        status = await controller.get_status()

    assert status.connected is True
    assert status.charging is True
    assert status.current_limit_a == 16.0


@pytest.mark.asyncio
async def test_external_stop_charging_keeps_evse_enabled():
    controller = ChargeAmpsExternalController(
        "2106037142M",
        api_key="valid-key",
        email="user@example.com",
        password="secret",
        use_mock=False,
    )
    settings_payload = {
        "chargePointId": "2106037142M",
        "connectorId": 1,
        "mode": "Off",
        "rfidLock": False,
        "maxCurrent": 16.0,
    }
    update = AsyncMock(return_value={})
    with (
        patch.object(
            controller._adapter._client,
            "get_connector_settings",
            AsyncMock(return_value=dict(settings_payload)),
        ),
        patch.object(controller._adapter._client, "update_connector_settings", update),
    ):
        await controller.stop_charging()

    assert update.await_args.args[0]["mode"] == "On"
    assert update.await_args.args[0]["maxCurrent"] == 0
