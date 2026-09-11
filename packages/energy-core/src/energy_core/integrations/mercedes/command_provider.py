"""Mercedes implementation of generic vehicle command provider."""

from __future__ import annotations

from energy_core.db.models import VehicleProviderConnectionModel
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.integrations.mercedes.commands import (
    MercedesCommandFeatures,
    build_charging_action_command,
    build_set_target_soc_command,
    describe_client_message,
)
from energy_core.providers.vehicle_integrations import build_mercedes_provider
from energy_core.vehicles.commands.errors import VehicleCommandError
from energy_core.vehicles.commands.provider_resolver import VehicleCommandDispatchResult


class MercedesVehicleCommandProvider:
    def __init__(
        self,
        row: VehicleProviderConnectionModel,
        repo: VehicleProviderRepository,
    ) -> None:
        self._row = row
        self._repo = repo

    async def load_command_features(self, vin: str) -> MercedesCommandFeatures:
        provider = self._build_provider()
        payload = await provider._rest.get_command_capabilities(vin)  # noqa: SLF001
        return MercedesCommandFeatures.from_rest_payload(payload)

    async def set_target_soc(
        self,
        vin: str,
        *,
        target_soc_percent: int,
        features: object,
    ) -> VehicleCommandDispatchResult:
        command_features = _as_mercedes_features(features)
        payload, request_id = build_set_target_soc_command(
            vin=vin,
            target_soc_percent=target_soc_percent,
            features=command_features,
        )
        status = await self._send(payload, request_id=request_id)
        return VehicleCommandDispatchResult(
            state=status.state,
            detail=describe_client_message(payload),
        )

    async def start_charging(self, vin: str, *, features: object) -> VehicleCommandDispatchResult:
        command_features = _as_mercedes_features(features)
        payload, request_id = build_charging_action_command(
            vin=vin,
            action="start",
            features=command_features,
        )
        status = await self._send(payload, request_id=request_id)
        return VehicleCommandDispatchResult(state=status.state)

    async def stop_charging(self, vin: str, *, features: object) -> VehicleCommandDispatchResult:
        command_features = _as_mercedes_features(features)
        payload, request_id = build_charging_action_command(
            vin=vin,
            action="stop",
            features=command_features,
        )
        status = await self._send(payload, request_id=request_id)
        return VehicleCommandDispatchResult(state=status.state)

    def _build_provider(self):
        token_bundle = self._repo.load_token_bundle(self._row)
        if token_bundle is None:
            raise VehicleCommandError("Vehicle provider is not authenticated", code="not_authenticated")
        return build_mercedes_provider(self._row, token_bundle=token_bundle)

    async def _send(self, payload: bytes, *, request_id: str):
        provider = self._build_provider()
        try:
            await provider.connect()
            return await provider.send_command_and_wait(payload, request_id=request_id)
        except TimeoutError as exc:
            raise VehicleCommandError(
                "Vehicle command timed out waiting for acknowledgement",
                code="command_timeout",
            ) from exc
        except VehicleCommandError:
            raise
        except Exception as exc:
            raise VehicleCommandError(str(exc), code="transport_failed") from exc
        finally:
            await provider.close()


def _as_mercedes_features(features: object) -> MercedesCommandFeatures:
    if isinstance(features, MercedesCommandFeatures):
        return features
    raise VehicleCommandError("Invalid vehicle command features", code="invalid_features")
