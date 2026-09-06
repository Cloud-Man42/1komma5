"""Zaptec REST charger adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from energy_core.chargers.framework.catalog import get_integration_method, get_model
from energy_core.chargers.framework.models import (
    ChargerCapabilities,
    ChargerStatus,
    ChargingSession,
    ConnectionTestResult,
    MeterValues,
    NormalizedChargerStatus,
)
from energy_core.integrations.zaptec.config import ZaptecConnectionInfo
from energy_core.integrations.zaptec.types import ZaptecChargerStatus


class ZaptecClientProtocol(Protocol):
    async def get_charger_status(self, charger_id: str) -> ZaptecChargerStatus: ...

    async def test_connection(self, charger_id: str) -> ZaptecChargerStatus: ...

    async def stop_charging(self, charger_id: str) -> None: ...

    async def resume_charging(self, charger_id: str) -> None: ...

    async def set_installation_available_current(
        self,
        installation_id: str,
        *,
        available_current_a: float,
    ) -> None: ...


class ZaptecRestAdapter:
    integration_method = "ZAPTEC_REST"

    def __init__(
        self,
        *,
        manufacturer_id: str,
        model_id: str,
        client: ZaptecClientProtocol,
        charger_id: str | None,
        installation_id: str | None,
        connection_info: ZaptecConnectionInfo,
    ) -> None:
        self._manufacturer_id = manufacturer_id
        self._model_id = model_id
        self._client = client
        self._charger_id = charger_id
        self._installation_id = installation_id
        self._connection_info = connection_info
        model = get_model(manufacturer_id, model_id)
        method = get_integration_method(self.integration_method)
        self._capabilities = model.capabilities if model else ChargerCapabilities(can_read_status=True)
        self._message = (
            f"Zaptec REST for {manufacturer_id}/{model_id} "
            f"({method.implementation_status if method else 'PLANNED'})."
        )

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    def _require_charger_id(self) -> str:
        if not self._charger_id:
            raise ValueError("Zaptec charger ID is not configured")
        return self._charger_id

    async def _read_status(self) -> ZaptecChargerStatus:
        return await self._client.get_charger_status(self._require_charger_id())

    async def get_status(self) -> NormalizedChargerStatus:
        status = await self._read_status()
        return NormalizedChargerStatus(
            online=status.online,
            vehicle_connected=status.vehicle_connected,
            charging=status.charging,
            state=status.state,
            timestamp=status.timestamp,
            configured_current_a=status.charge_current_a,
            power_w=status.power_w,
        )

    async def get_legacy_status(self) -> ChargerStatus:
        return ChargerStatus.from_normalized(await self.get_status())

    async def get_capabilities(self) -> ChargerCapabilities:
        return self._capabilities

    async def start_charging(self) -> None:
        await self._client.resume_charging(self._require_charger_id())

    async def stop_charging(self) -> None:
        await self._client.stop_charging(self._require_charger_id())

    async def get_requested_current(self) -> float | None:
        status = await self._read_status()
        return status.charge_current_a

    async def get_actual_current(self) -> float | None:
        status = await self._read_status()
        return status.charge_current_a

    async def set_max_current(self, amps: float) -> None:
        if not self._installation_id:
            raise ValueError("Zaptec installation ID is required for current control")
        await self._client.set_installation_available_current(
            self._installation_id,
            available_current_a=amps,
        )

    async def get_power(self) -> float | None:
        status = await self._read_status()
        return status.power_w

    async def get_energy(self) -> float | None:
        status = await self._read_status()
        return status.session_energy_kwh

    async def get_session(self) -> ChargingSession | None:
        return None

    async def get_meter_values(self) -> MeterValues | None:
        status = await self._read_status()
        return MeterValues(
            timestamp=status.timestamp or datetime.now(UTC),
            power_w=status.power_w,
            energy_kwh=status.session_energy_kwh,
        )

    async def test_connection(self) -> ConnectionTestResult:
        try:
            status = await self._read_status()
        except Exception as exc:
            return ConnectionTestResult(
                success=False,
                status="ERROR",
                message=str(exc),
                capabilities=self._capabilities,
            )
        if self._connection_info.mock:
            return ConnectionTestResult(
                success=True,
                status="MOCK",
                message="Zaptec mock client returned status successfully.",
                capabilities=self._capabilities,
            )
        return ConnectionTestResult(
            success=status.online,
            status=status.state,
            message=f"Zaptec charger online={status.online} state={status.state}",
            capabilities=self._capabilities,
        )
