"""Pull fresh vehicle snapshots from Mercedes me REST and persist them."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository, _carries_telemetry
from energy_core.secrets import SecretBox, SecretBoxError
from energy_core.vehicles.abstractions.models import VehicleState
from energy_core.vehicles.correlation.repo import VehicleHaloCorrelationRepository
from energy_core.vehicles.mercedes.auth.errors import MercedesAuthError
from energy_core.vehicles.mercedes.provider import MercedesProvider

logger = logging.getLogger(__name__)


class VehicleSyncError(Exception):
    def __init__(self, message: str, *, code: str = "sync_failed") -> None:
        super().__init__(message)
        self.code = code


class VehicleSyncService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        secret_box: SecretBox | None = None,
        is_sqlite: bool = False,
    ) -> None:
        self._session = session
        self._provider_repo = VehicleProviderRepository(session, secret_box=secret_box)
        self._vehicle_repo = VehicleRepository(session, is_sqlite=is_sqlite)
        self._is_sqlite = is_sqlite

    async def sync_site(self, site_id: int) -> tuple[VehicleState, ...]:
        row = await self._provider_repo.get_for_site(site_id)
        if row is None or not row.enabled:
            raise VehicleSyncError("Mercedes integration is not enabled", code="integration_disabled")

        try:
            token_bundle = self._provider_repo.load_token_bundle(row)
        except SecretBoxError as exc:
            raise VehicleSyncError(
                "Stored Mercedes credentials cannot be decrypted. Re-save your password.",
                code="credentials_stale",
            ) from exc

        if token_bundle is None:
            raise VehicleSyncError("Mercedes is not authenticated", code="not_authenticated")

        provider = MercedesProvider(
            region=row.region,
            device_guid=row.device_guid or str(uuid.uuid4()),
            token_bundle=token_bundle,
        )
        enabled_vehicles = await self._vehicle_repo.list_for_site(site_id)
        enabled_vins = tuple(
            (vehicle.vin or vehicle.external_id)
            for vehicle in enabled_vehicles
            if vehicle.enabled and (vehicle.vin or vehicle.external_id)
        )
        enabled_external_ids = {
            vehicle.external_id for vehicle in enabled_vehicles if vehicle.enabled
        }
        enabled_vin_set = set(enabled_vins)
        try:
            states = await provider.sync_from_rest(vins=enabled_vins or None)
        except MercedesAuthError as exc:
            raise VehicleSyncError(str(exc), code="auth_failed") from exc
        except Exception as exc:
            logger.exception("Mercedes REST sync failed for site_id=%s", site_id)
            raise VehicleSyncError(str(exc), code="transport_failed") from exc
        finally:
            await provider.close()

        relevant_states = tuple(
            state
            for state in states
            if state.vehicle_id in enabled_external_ids
            or (state.vin is not None and state.vin in enabled_vin_set)
        )
        fresh_states = tuple(state for state in relevant_states if _carries_telemetry(state))
        if not fresh_states:
            raise VehicleSyncError(
                "Mercedes me returned no fresh vehicle telemetry",
                code="no_telemetry",
            )

        updated: list[VehicleState] = []
        for state in fresh_states:
            existing = await self._vehicle_repo.get_by_external_id(
                site_id=site_id,
                provider=state.provider,
                external_id=state.vehicle_id,
            )
            if existing is not None and not existing.enabled:
                continue
            db_vehicle = await self._vehicle_repo.upsert_vehicle(
                site_id=site_id,
                provider=state.provider,
                external_id=state.vehicle_id,
                vin=state.vin,
                manufacturer=state.manufacturer,
                model=state.model,
                display_name=state.model,
            )
            await self._vehicle_repo.upsert_capabilities(db_vehicle.id, state.capabilities)
            await self._vehicle_repo.persist_state(db_vehicle.id, state)
            await VehicleHaloCorrelationRepository(self._session).correlate_and_persist(db_vehicle, state)
            updated.append(state)

        await self._provider_repo.update_runtime_status(
            row,
            connection_state="CONNECTED",
            last_error="",
        )
        return tuple(updated)
