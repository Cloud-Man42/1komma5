"""Placeholder adapter for catalog entries without a verified implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.chargers.framework.catalog import get_integration_method, get_model
from energy_core.chargers.framework.models import (
    ChargerCapabilities,
    ChargerStatus,
    ChargingSession,
    ConnectionTestResult,
    MeterValues,
    NormalizedChargerStatus,
)


class UnsupportedChargerAdapter:
    """Returns explicit unsupported errors instead of fake API behaviour."""

    def __init__(
        self,
        *,
        manufacturer_id: str,
        model_id: str,
        integration_method: str,
    ) -> None:
        self._manufacturer_id = manufacturer_id
        self._model_id = model_id
        self._integration_method = integration_method
        model = get_model(manufacturer_id, model_id)
        method = get_integration_method(integration_method)
        self._capabilities = model.capabilities if model else ChargerCapabilities(can_read_status=False)
        self._message = (
            f"Integration {integration_method} for {manufacturer_id}/{model_id} "
            f"is not implemented yet ({method.implementation_status if method else 'UNSUPPORTED'})."
        )

    async def connect(self) -> None:
        raise UnsupportedOperationError(self._message)

    async def disconnect(self) -> None:
        return None

    async def get_status(self) -> NormalizedChargerStatus:
        return NormalizedChargerStatus(
            online=False,
            vehicle_connected=False,
            charging=False,
            state="OFFLINE",
            timestamp=datetime.now(UTC),
        )

    async def get_legacy_status(self) -> ChargerStatus:
        status = await self.get_status()
        return ChargerStatus.from_normalized(status)

    async def get_capabilities(self) -> ChargerCapabilities:
        return self._capabilities

    async def start_charging(self) -> None:
        raise UnsupportedOperationError(self._message)

    async def stop_charging(self) -> None:
        raise UnsupportedOperationError(self._message)

    async def get_requested_current(self) -> float | None:
        return None

    async def get_actual_current(self) -> float | None:
        return None

    async def set_max_current(self, amps: float) -> None:
        raise UnsupportedOperationError(self._message)

    async def get_power(self) -> float | None:
        return None

    async def get_energy(self) -> float | None:
        return None

    async def get_session(self) -> ChargingSession | None:
        return None

    async def get_meter_values(self) -> MeterValues | None:
        return None

    async def test_connection(self) -> ConnectionTestResult:
        method = get_integration_method(self._integration_method)
        if method and method.protocol.startswith("OCPP"):
            return ConnectionTestResult(
                success=False,
                status="UNSUPPORTED",
                message="EMIC OCPP CSMS är inte konfigurerad ännu.",
            )
        return ConnectionTestResult(
            success=False,
            status="UNSUPPORTED",
            message=self._message,
            capabilities=self._capabilities,
        )


class UnsupportedOperationError(Exception):
    pass
