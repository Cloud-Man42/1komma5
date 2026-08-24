"""Tests for Mercedes vehicle command builder and service."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.db.models import VehicleCapabilityModel, VehicleModel, VehicleProviderConnectionModel
from energy_core.vehicles.commands.errors import VehicleCommandsDisabledError
from energy_core.vehicles.commands.service import VehicleCommandService
from energy_core.vehicles.mercedes.commands.builder import (
    build_charging_action_command,
    build_set_target_soc_command,
    describe_client_message,
)
from energy_core.vehicles.mercedes.commands.features import MercedesCommandFeatures
from energy_core.vehicles.mercedes.commands.response import MercedesCommandStatus
from energy_core.vehicles.mercedes.protocol.proto import client_pb2, vehicle_commands_pb2


def test_build_set_target_soc_uses_charging_configure_for_eqe():
    features = MercedesCommandFeatures(charging_configure=True)
    payload, request_id = build_set_target_soc_command(
        vin="W1KTESTVIN0000001",
        target_soc_percent=85,
        features=features,
    )
    message = client_pb2.ClientMessage()
    message.ParseFromString(payload)
    assert request_id
    assert message.tracking_id
    assert message.commandRequest.vin == "W1KTESTVIN0000001"
    assert message.commandRequest.charging_configure.max_soc.value == 85
    assert describe_client_message(payload) == "charging_configure, max_soc=85"


def test_build_set_target_soc_uses_battery_max_soc_fallback():
    features = MercedesCommandFeatures(battery_max_soc_configure=True)
    payload, _request_id = build_set_target_soc_command(
        vin="W1KTESTVIN0000001",
        target_soc_percent=85,
        features=features,
    )
    message = client_pb2.ClientMessage()
    message.ParseFromString(payload)
    assert message.commandRequest.battery_max_soc.max_soc == 85


def test_build_charging_action_command_start():
    features = MercedesCommandFeatures(charging_configure=True)
    payload, request_id = build_charging_action_command(vin="W1KTESTVIN0000001", action="start", features=features)
    message = client_pb2.ClientMessage()
    message.ParseFromString(payload)
    assert request_id
    assert message.commandRequest.charging_configure.action == vehicle_commands_pb2.ChargingConfigure.START


def test_build_charging_action_command_stop():
    features = MercedesCommandFeatures(charging_configure=True)
    payload, _request_id = build_charging_action_command(vin="W1KTESTVIN0000001", action="stop", features=features)
    message = client_pb2.ClientMessage()
    message.ParseFromString(payload)
    assert message.commandRequest.charging_configure.action == vehicle_commands_pb2.ChargingConfigure.STOP


def test_command_features_from_rest_commands_list():
    features = MercedesCommandFeatures.from_rest_payload(
        {
            "commands": [
                {"commandName": "BATTERY_MAX_SOC_CONFIGURE", "isAvailable": True},
                {"commandName": "CHARGE_COUPLER_STOP", "isAvailable": True},
            ]
        }
    )
    assert features.battery_max_soc_configure is True
    assert features.charge_coupler_stop is True
    assert features.supports_set_target_soc() is True
    assert features.supports_stop_charging() is True
    assert features.supports_start_charging() is False


def test_build_set_target_soc_uses_battery_max_soc_for_eqe():
    features = MercedesCommandFeatures(battery_max_soc_configure=True)
    payload, _request_id = build_set_target_soc_command(
        vin="W1KTESTVIN0000001",
        target_soc_percent=85,
        features=features,
    )
    message = client_pb2.ClientMessage()
    message.ParseFromString(payload)
    assert message.commandRequest.battery_max_soc.max_soc == 85
    assert describe_client_message(payload) == "battery_max_soc.max_soc=85"


def test_build_stop_charging_uses_charge_coupler_stop():
    features = MercedesCommandFeatures(charge_coupler_stop=True)
    payload, _request_id = build_charging_action_command(
        vin="W1KTESTVIN0000001",
        action="stop",
        features=features,
    )
    assert describe_client_message(payload) == "charge_coupler_stop"


@pytest.mark.asyncio
async def test_command_service_rejects_when_disabled():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=False,
    )
    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)

    with pytest.raises(VehicleCommandsDisabledError):
        await service.set_target_soc(site_id=1, vehicle_id=1, target_soc_percent=80)


@pytest.mark.asyncio
async def test_command_service_set_target_soc_sends_payload():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        region="Europe",
        device_guid="device",
        encrypted_access_token="x",
        encrypted_refresh_token="y",
        token_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    vehicle = VehicleModel(
        id=3,
        site_id=1,
        provider="mercedes",
        external_id="eqe",
        manufacturer="Mercedes-Benz",
        model="EQE",
        display_name="EQE",
        enabled=True,
        vin="W1KTESTVIN0000001",
    )
    cap = VehicleCapabilityModel(vehicle_id=3, capability="can_set_target_soc", available=True)

    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)
    service._provider_repo.load_token_bundle = MagicMock(return_value=object())
    session.get = AsyncMock(return_value=vehicle)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cap)))

    with patch("energy_core.vehicles.commands.service.MercedesProvider") as provider_cls:
        provider = AsyncMock()
        provider._rest.get_command_capabilities = AsyncMock(  # noqa: SLF001
            return_value={"commands": ["CHARGING_CONFIGURE"]}
        )
        provider.send_command_and_wait = AsyncMock(
            return_value=MercedesCommandStatus(request_id="req", state="FINISHED")
        )
        provider_cls.return_value = provider
        result = await service.set_target_soc(site_id=1, vehicle_id=3, target_soc_percent=80)

    assert result.success is True
    provider.connect.assert_awaited_once()
    provider.send_command_and_wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_command_service_pushes_heartbeat_target_soc_on_success():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        region="Europe",
        device_guid="device",
        encrypted_access_token="x",
        encrypted_refresh_token="y",
        token_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    vehicle = VehicleModel(
        id=3,
        site_id=1,
        provider="mercedes",
        external_id="eqe",
        manufacturer="Mercedes-Benz",
        model="EQE",
        display_name="EQE",
        enabled=True,
        vin="W1KTESTVIN0000001",
        charger_id=4,
    )
    cap = VehicleCapabilityModel(vehicle_id=3, capability="can_set_target_soc", available=True)
    charger = SimpleNamespace(id=4, heartbeat_sync_enabled=True, heartbeat_ev_id="ev-1")
    site = SimpleNamespace(id=1, external_system_id="sys-1")

    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)
    service._provider_repo.load_token_bundle = MagicMock(return_value=object())
    session.get = AsyncMock(side_effect=lambda model, pk: vehicle if model is VehicleModel else site)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cap)))

    push_mock = AsyncMock(return_value=SimpleNamespace(pushed=True))
    get_charger_mock = AsyncMock(return_value=charger)

    with (
        patch("energy_core.vehicles.commands.service.MercedesProvider") as provider_cls,
        patch("energy_core.vehicles.commands.service.EvChargerRepository") as charger_repo_cls,
        patch("energy_core.vehicles.commands.service.HeartbeatEvSyncService") as sync_cls,
    ):
        charger_repo_cls.return_value.get_by_id = get_charger_mock
        sync_cls.return_value.push_charger = push_mock
        provider = AsyncMock()
        provider._rest.get_command_capabilities = AsyncMock(  # noqa: SLF001
            return_value={"commands": ["CHARGING_CONFIGURE"]}
        )
        provider.send_command_and_wait = AsyncMock(
            return_value=MercedesCommandStatus(request_id="req", state="FINISHED")
        )
        provider_cls.return_value = provider
        result = await service.set_target_soc(site_id=1, vehicle_id=3, target_soc_percent=80)

    assert result.success is True
    push_mock.assert_awaited_once()
    kwargs = push_mock.await_args.kwargs
    assert kwargs["target_soc_pct"] == 80.0
    provider.close.assert_awaited_once()
