"""Charge Amps Halo adapter backed by External API v5."""

from __future__ import annotations

from typing import Any, Protocol

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.capabilities import ChargerCapabilities
from energy_core.chargers.client import DEFAULT_CONNECTOR_ID, ChargeAmpsClient
from energy_core.chargers.errors import ChargerApiError
from energy_core.chargers.vehicle_status import vehicle_connected_from_external_connector


class ChargerAdapter(Protocol):
    async def get_status(self) -> ChargerStatus: ...

    async def start_charging(self) -> None: ...

    async def stop_charging(self) -> None: ...

    async def set_current(self, amps: float) -> None: ...

    async def get_current(self) -> float: ...

    async def get_power(self) -> float: ...

    async def get_capabilities(self) -> ChargerCapabilities: ...


class ChargeAmpsHaloAdapter:
    """Vendor-specific adapter for Charge Amps Halo via External API v5."""

    def __init__(
        self,
        client: ChargeAmpsClient,
        *,
        min_current_a: float = 6.0,
        max_current_a: float = 16.0,
        phases: int = 3,
    ) -> None:
        self._client = client
        self._min_current_a = min_current_a
        self._max_current_a = max_current_a
        self._phases = phases
        self._last_known_current_a: float | None = None
        self._last_error: ChargerApiError | None = None

    @property
    def last_error(self) -> ChargerApiError | None:
        return self._last_error

    async def get_status(self) -> ChargerStatus:
        try:
            status_payload = await self._client.get_chargepoint_status()
            settings = await self._client.get_connector_settings()
            connector = _connector_by_id(
                status_payload.get("connectorStatuses") or status_payload.get("connector_statuses") or [],
                self._client._connector_id,
            ) or {}
            connector_status = str(connector.get("status") or connector.get("ocppStatus") or "")
            current = _float_or_none(settings.get("maxCurrent"))
            self._last_known_current_a = current
            self._last_error = None
            charging = connector_status.casefold() == "charging" or bool(
                connector.get("isCharging") or connector.get("is_charging")
            )
            return ChargerStatus(
                connected=True,
                vehicle_connected=vehicle_connected_from_external_connector(connector),
                current_limit_a=current,
                charging=charging,
            )
        except ChargerApiError as exc:
            self._last_error = exc
            if exc.code in {"AUTH_ERROR", "CHARGER_OFFLINE", "TIMEOUT"}:
                return ChargerStatus(
                    connected=False,
                    vehicle_connected=False,
                    current_limit_a=self._last_known_current_a,
                    charging=False,
                )
            raise

    async def set_current(self, amps: float) -> None:
        settings = await self._client.get_connector_settings(force=True)
        current = _float_or_none(settings.get("maxCurrent"))
        if current is not None and abs(current - amps) < 0.01:
            return
        settings["maxCurrent"] = amps
        await self._client.update_connector_settings(settings)
        self._last_known_current_a = amps

    async def set_current_limit(self, amps: float) -> None:
        await self.set_current(amps)

    async def get_current(self) -> float:
        settings = await self._client.get_connector_settings()
        return _float_or_none(settings.get("maxCurrent")) or 0.0

    async def get_power(self) -> float:
        return 0.0

    async def start_charging(self) -> None:
        settings = await self._client.get_connector_settings(force=True)
        if str(settings.get("mode", "")).lower() == "on":
            return
        settings["mode"] = "On"
        await self._client.update_connector_settings(settings)

    async def stop_charging(self) -> None:
        settings = await self._client.get_connector_settings(force=True)
        if settings.get("rfidLock"):
            await self._client.remote_stop()
            self._last_known_current_a = 0.0
            return
        # Keep the EVSE enabled so a plugged-in car stays visible as Preparing/SuspendedEV.
        settings["mode"] = "On"
        settings["maxCurrent"] = 0
        await self._client.update_connector_settings(settings)
        self._last_known_current_a = 0.0

    async def is_connected(self) -> bool:
        status = await self.get_status()
        return status.connected

    async def is_vehicle_connected(self) -> bool:
        status = await self.get_status()
        return status.vehicle_connected

    async def get_capabilities(self) -> ChargerCapabilities:
        return ChargerCapabilities(
            min_current_a=self._min_current_a,
            max_current_a=self._max_current_a,
            phases=self._phases,
            supports_current_control=True,
            supports_remote_start_stop=True,
            supports_power_reading=False,
            supports_dynamic_phases=False,
        )


def _connector_by_id(connectors: list[Any], connector_id: int) -> dict[str, Any] | None:
    for connector in connectors:
        if not isinstance(connector, dict):
            continue
        current_id = connector.get("connectorId", connector.get("connector_id"))
        if current_id == connector_id:
            return connector
    return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_halo_adapter(
    charger_id: str,
    *,
    api_key: str,
    email: str,
    password: str,
    connector_id: int = DEFAULT_CONNECTOR_ID,
    min_current_a: float = 6.0,
    max_current_a: float = 16.0,
    phases: int = 3,
) -> ChargeAmpsHaloAdapter:
    client = ChargeAmpsClient(
        charger_id=charger_id,
        api_key=api_key,
        email=email,
        password=password,
        connector_id=connector_id,
    )
    return ChargeAmpsHaloAdapter(
        client,
        min_current_a=min_current_a,
        max_current_a=max_current_a,
        phases=phases,
    )
