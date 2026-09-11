"""Dispatch vehicle commands with feature-flag and capability guards."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleCapabilityModel, VehicleModel
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.secrets import SecretBox
from energy_core.vehicles.abstractions.models import VehicleCommandResult
from energy_core.vehicles.commands.errors import (
    VehicleCapabilityUnavailableError,
    VehicleCommandError,
    VehicleCommandsDisabledError,
)
from energy_core.providers.vehicle_command_wiring import resolve_vehicle_command_provider

logger = logging.getLogger(__name__)


class VehicleCommandService:
    def __init__(self, session: AsyncSession, *, secret_box: SecretBox | None = None) -> None:
        self._session = session
        self._secret_box = secret_box
        self._provider_repo = VehicleProviderRepository(session, secret_box=secret_box)

    async def set_target_soc(self, *, site_id: int, vehicle_id: int, target_soc_percent: int) -> VehicleCommandResult:
        await self._ensure_commands_enabled(site_id)
        vehicle = await self._get_vehicle(site_id, vehicle_id)
        await self._require_capability(vehicle.id, "can_set_target_soc")
        if not 30 <= target_soc_percent <= 100:
            raise VehicleCommandError("target_soc must be between 30 and 100", code="invalid_target_soc")
        vin = self._require_vin(vehicle)
        provider = await self._resolve_provider(site_id)
        features = await provider.load_command_features(vin)
        result = await provider.set_target_soc(vin, target_soc_percent=target_soc_percent, features=features)
        return VehicleCommandResult(
            success=_is_successful_status(result.state),
            message=f"Target SoC command {result.state}: {result.detail}".strip(": "),
            vehicle_id=str(vehicle.id),
            command="set_target_soc",
        )

    async def start_charging(self, *, site_id: int, vehicle_id: int) -> VehicleCommandResult:
        await self._ensure_commands_enabled(site_id)
        vehicle = await self._get_vehicle(site_id, vehicle_id)
        await self._require_capability(vehicle.id, "can_start_charging")
        vin = self._require_vin(vehicle)
        provider = await self._resolve_provider(site_id)
        features = await provider.load_command_features(vin)
        result = await provider.start_charging(vin, features=features)
        return VehicleCommandResult(
            success=_is_successful_status(result.state),
            message=f"Start charging command {result.state}",
            vehicle_id=str(vehicle.id),
            command="start_charging",
        )

    async def stop_charging(self, *, site_id: int, vehicle_id: int) -> VehicleCommandResult:
        await self._ensure_commands_enabled(site_id)
        vehicle = await self._get_vehicle(site_id, vehicle_id)
        await self._require_capability(vehicle.id, "can_stop_charging")
        vin = self._require_vin(vehicle)
        provider = await self._resolve_provider(site_id)
        features = await provider.load_command_features(vin)
        result = await provider.stop_charging(vin, features=features)
        return VehicleCommandResult(
            success=_is_successful_status(result.state),
            message=f"Stop charging command {result.state}",
            vehicle_id=str(vehicle.id),
            command="stop_charging",
        )

    async def _ensure_commands_enabled(self, site_id: int) -> None:
        row = await self._provider_repo.get_for_site(site_id)
        if row is None or not row.enabled or not row.commands_enabled:
            raise VehicleCommandsDisabledError()

    async def _get_vehicle(self, site_id: int, vehicle_id: int) -> VehicleModel:
        vehicle = await self._session.get(VehicleModel, vehicle_id)
        if vehicle is None or vehicle.site_id != site_id or not vehicle.enabled:
            raise VehicleCommandError("Vehicle not found", code="vehicle_not_found")
        return vehicle

    async def _require_capability(self, vehicle_id: int, capability: str) -> None:
        result = await self._session.execute(
            select(VehicleCapabilityModel).where(
                VehicleCapabilityModel.vehicle_id == vehicle_id,
                VehicleCapabilityModel.capability == capability,
            )
        )
        row = result.scalar_one_or_none()
        if row is None or not row.available:
            raise VehicleCapabilityUnavailableError(capability)

    def _require_vin(self, vehicle: VehicleModel) -> str:
        if not vehicle.vin:
            raise VehicleCommandError("Vehicle VIN unavailable", code="vin_unavailable")
        return vehicle.vin

    async def _resolve_provider(self, site_id: int):
        provider = await resolve_vehicle_command_provider(
            self._session,
            site_id,
            secret_box=self._secret_box,
        )
        if provider is None:
            raise VehicleCommandError("Vehicle integration not configured", code="integration_missing")
        return provider


def _is_successful_status(state: str) -> bool:
    normalized = state.upper()
    return normalized in {"FINISHED", "SUCCESS", "ACKED_BY_APPTWIN", "5", "7"}
