"""Dispatch vehicle commands with feature-flag and capability guards."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleCapabilityModel, VehicleModel, VehicleProviderConnectionModel
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.secrets import SecretBox
from energy_core.vehicles.abstractions.models import VehicleCommandResult
from energy_core.vehicles.commands.errors import (
    VehicleCapabilityUnavailableError,
    VehicleCommandError,
    VehicleCommandsDisabledError,
)
from energy_core.vehicles.mercedes.commands.builder import (
    build_charging_action_command,
    build_set_target_soc_command,
    describe_client_message,
)
from energy_core.vehicles.mercedes.commands.features import MercedesCommandFeatures
from energy_core.vehicles.mercedes.provider import MercedesProvider

logger = logging.getLogger(__name__)


class VehicleCommandService:
    def __init__(self, session: AsyncSession, *, secret_box: SecretBox | None = None) -> None:
        self._session = session
        self._provider_repo = VehicleProviderRepository(session, secret_box=secret_box)

    async def set_target_soc(self, *, site_id: int, vehicle_id: int, target_soc_percent: int) -> VehicleCommandResult:
        await self._ensure_commands_enabled(site_id)
        vehicle = await self._get_vehicle(site_id, vehicle_id)
        await self._require_capability(vehicle.id, "can_set_target_soc")
        if not 30 <= target_soc_percent <= 100:
            raise VehicleCommandError("target_soc must be between 30 and 100", code="invalid_target_soc")
        vin = self._require_vin(vehicle)
        features = await self._load_command_features(site_id, vin)
        payload, request_id = build_set_target_soc_command(
            vin=vin,
            target_soc_percent=target_soc_percent,
            features=features,
        )
        status = await self._send_mercedes_command(site_id, payload, request_id=request_id)
        return VehicleCommandResult(
            success=_is_successful_status(status.state),
            message=f"Target SoC command {status.state}: {describe_client_message(payload)}",
            vehicle_id=str(vehicle.id),
            command="set_target_soc",
        )

    async def start_charging(self, *, site_id: int, vehicle_id: int) -> VehicleCommandResult:
        await self._ensure_commands_enabled(site_id)
        vehicle = await self._get_vehicle(site_id, vehicle_id)
        await self._require_capability(vehicle.id, "can_start_charging")
        vin = self._require_vin(vehicle)
        features = await self._load_command_features(site_id, vin)
        payload, request_id = build_charging_action_command(vin=vin, action="start", features=features)
        status = await self._send_mercedes_command(site_id, payload, request_id=request_id)
        return VehicleCommandResult(
            success=_is_successful_status(status.state),
            message=f"Start charging command {status.state}",
            vehicle_id=str(vehicle.id),
            command="start_charging",
        )

    async def stop_charging(self, *, site_id: int, vehicle_id: int) -> VehicleCommandResult:
        await self._ensure_commands_enabled(site_id)
        vehicle = await self._get_vehicle(site_id, vehicle_id)
        await self._require_capability(vehicle.id, "can_stop_charging")
        vin = self._require_vin(vehicle)
        features = await self._load_command_features(site_id, vin)
        payload, request_id = build_charging_action_command(vin=vin, action="stop", features=features)
        status = await self._send_mercedes_command(site_id, payload, request_id=request_id)
        return VehicleCommandResult(
            success=_is_successful_status(status.state),
            message=f"Stop charging command {status.state}",
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

    async def _load_command_features(self, site_id: int, vin: str) -> MercedesCommandFeatures:
        row = await self._provider_repo.get_for_site(site_id)
        if row is None:
            raise VehicleCommandError("Mercedes integration not configured", code="integration_missing")
        token_bundle = self._provider_repo.load_token_bundle(row)
        if token_bundle is None:
            raise VehicleCommandError("Mercedes is not authenticated", code="not_authenticated")
        provider = MercedesProvider(
            region=row.region,
            device_guid=row.device_guid or None,
            token_bundle=token_bundle,
        )
        payload = await provider._rest.get_command_capabilities(vin)  # noqa: SLF001
        return MercedesCommandFeatures.from_rest_payload(payload)

    async def _send_mercedes_command(
        self,
        site_id: int,
        payload: bytes,
        *,
        request_id: str,
    ):
        row = await self._provider_repo.get_for_site(site_id)
        if row is None:
            raise VehicleCommandError("Mercedes integration not configured", code="integration_missing")
        token_bundle = self._provider_repo.load_token_bundle(row)
        if token_bundle is None:
            raise VehicleCommandError("Mercedes is not authenticated", code="not_authenticated")
        provider = MercedesProvider(
            region=row.region,
            device_guid=row.device_guid or None,
            token_bundle=token_bundle,
        )
        try:
            await provider.connect()
            return await provider.send_command_and_wait(payload, request_id=request_id)
        except TimeoutError as exc:
            raise VehicleCommandError("Mercedes command timed out waiting for acknowledgement", code="command_timeout") from exc
        except Exception as exc:
            logger.exception("Mercedes command failed site_id=%s", site_id)
            raise VehicleCommandError(str(exc), code="transport_failed") from exc
        finally:
            await provider.close()


def _is_successful_status(state: str) -> bool:
    normalized = state.upper()
    return normalized in {"FINISHED", "SUCCESS", "ACKED_BY_APPTWIN", "5", "7"}
