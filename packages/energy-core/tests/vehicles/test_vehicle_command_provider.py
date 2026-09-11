"""Tests for generic vehicle command provider resolution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.db.models import VehicleCapabilityModel, VehicleModel, VehicleProviderConnectionModel
from energy_core.providers.vehicle_command_wiring import resolve_vehicle_command_provider
from energy_core.vehicles.commands.errors import (
    VehicleCapabilityUnavailableError,
    VehicleCommandError,
    VehicleCommandsDisabledError,
)
from energy_core.vehicles.commands.mock_provider import MockVehicleCommandProvider
from energy_core.vehicles.commands.service import VehicleCommandService


@pytest.mark.asyncio
async def test_resolve_mock_vehicle_command_provider():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        provider="mock",
    )
    with patch("energy_core.providers.vehicle_command_wiring.VehicleProviderRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_for_site = AsyncMock(return_value=row)
        provider = await resolve_vehicle_command_provider(session, site_id=1)
    assert isinstance(provider, MockVehicleCommandProvider)


@pytest.mark.asyncio
async def test_resolve_unsupported_provider_raises():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        provider="unknown-vendor",
    )
    with patch("energy_core.providers.vehicle_command_wiring.VehicleProviderRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_for_site = AsyncMock(return_value=row)
        with pytest.raises(VehicleCommandError, match="not supported"):
            await resolve_vehicle_command_provider(session, site_id=1)


@pytest.mark.asyncio
async def test_command_service_uses_mock_provider_without_mercedes():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        provider="mock",
    )
    vehicle = VehicleModel(
        id=3,
        site_id=1,
        provider="mock",
        external_id="mock-1",
        manufacturer="Mock",
        model="EV",
        display_name="Mock EV",
        enabled=True,
        vin="MOCKVIN000000001",
    )
    cap = VehicleCapabilityModel(vehicle_id=3, capability="can_start_charging", available=True)
    mock_provider = MockVehicleCommandProvider()

    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)
    session.get = AsyncMock(return_value=vehicle)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cap)))

    with patch(
        "energy_core.vehicles.commands.service.resolve_vehicle_command_provider",
        AsyncMock(return_value=mock_provider),
    ):
        result = await service.start_charging(site_id=1, vehicle_id=3)

    assert result.success is True
    assert "start:MOCKVIN000000001" in mock_provider.calls


@pytest.mark.asyncio
async def test_command_service_rejects_unsupported_capability():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        provider="mock",
    )
    vehicle = VehicleModel(
        id=3,
        site_id=1,
        provider="mock",
        external_id="mock-1",
        manufacturer="Mock",
        model="EV",
        display_name="Mock EV",
        enabled=True,
        vin="MOCKVIN000000001",
    )
    cap = VehicleCapabilityModel(vehicle_id=3, capability="can_start_charging", available=False)

    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)
    session.get = AsyncMock(return_value=vehicle)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cap)))

    with pytest.raises(VehicleCapabilityUnavailableError):
        await service.start_charging(site_id=1, vehicle_id=3)


@pytest.mark.asyncio
async def test_command_service_wrong_site_vehicle():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        provider="mock",
    )
    vehicle = VehicleModel(
        id=3,
        site_id=99,
        provider="mock",
        external_id="mock-1",
        manufacturer="Mock",
        model="EV",
        display_name="Mock EV",
        enabled=True,
        vin="MOCKVIN000000001",
    )

    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)
    session.get = AsyncMock(return_value=vehicle)

    with pytest.raises(VehicleCommandError, match="not found"):
        await service.start_charging(site_id=1, vehicle_id=3)


@pytest.mark.asyncio
async def test_command_service_provider_unavailable():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=True,
        provider="mock",
    )
    vehicle = VehicleModel(
        id=3,
        site_id=1,
        provider="mock",
        external_id="mock-1",
        manufacturer="Mock",
        model="EV",
        display_name="Mock EV",
        enabled=True,
        vin="MOCKVIN000000001",
    )
    cap = VehicleCapabilityModel(vehicle_id=3, capability="can_stop_charging", available=True)
    mock_provider = MockVehicleCommandProvider(fail=True)

    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)
    session.get = AsyncMock(return_value=vehicle)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cap)))

    with patch(
        "energy_core.vehicles.commands.service.resolve_vehicle_command_provider",
        AsyncMock(return_value=mock_provider),
    ):
        with pytest.raises(VehicleCommandError, match="mock failure"):
            await service.stop_charging(site_id=1, vehicle_id=3)


@pytest.mark.asyncio
async def test_command_service_commands_disabled_still_raises():
    session = AsyncMock()
    row = VehicleProviderConnectionModel(
        id=1,
        site_id=1,
        enabled=True,
        commands_enabled=False,
        provider="mock",
    )
    service = VehicleCommandService(session)
    service._provider_repo.get_for_site = AsyncMock(return_value=row)

    with pytest.raises(VehicleCommandsDisabledError):
        await service.start_charging(site_id=1, vehicle_id=1)
