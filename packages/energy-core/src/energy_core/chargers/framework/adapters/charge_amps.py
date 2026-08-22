"""Wrap legacy Charge Amps Halo adapter in the vendor-neutral framework contract."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.chargers.framework.models import (
    ChargerCapabilities,
    ChargerStatus,
    ChargingSession,
    ConnectionTestResult,
    DetectedDevice,
    MeterValues,
    NormalizedChargerStatus,
)
from energy_core.chargers.halo_adapter import ChargeAmpsHaloAdapter


class ChargeAmpsFrameworkAdapter:
    """Framework adapter delegating to ChargeAmpsHaloAdapter."""

    def __init__(
        self,
        inner: ChargeAmpsHaloAdapter,
        *,
        charger_id: str,
        manufacturer_id: str = "charge-amps",
        model_id: str = "halo",
    ) -> None:
        self._inner = inner
        self._charger_id = charger_id
        self._manufacturer_id = manufacturer_id
        self._model_id = model_id
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def get_status(self) -> NormalizedChargerStatus:
        legacy = await self._inner.get_status()
        return _normalize(legacy)

    async def get_legacy_status(self) -> ChargerStatus:
        return await self._inner.get_status()

    async def get_capabilities(self) -> ChargerCapabilities:
        legacy = await self._inner.get_capabilities()
        return ChargerCapabilities.from_legacy(
            min_current_a=legacy.min_current_a,
            max_current_a=legacy.max_current_a,
            phases=legacy.phases,
            supports_current_control=legacy.supports_current_control,
            supports_remote_start_stop=legacy.supports_remote_start_stop,
            supports_power_reading=legacy.supports_power_reading,
            supports_dynamic_phases=legacy.supports_dynamic_phases,
        )

    async def start_charging(self) -> None:
        await self._inner.start_charging()

    async def stop_charging(self) -> None:
        await self._inner.stop_charging()

    async def get_requested_current(self) -> float | None:
        current = await self._inner.get_current()
        return current if current > 0 else None

    async def get_actual_current(self) -> float | None:
        return await self.get_requested_current()

    async def set_max_current(self, amps: float) -> None:
        await self._inner.set_current(amps)

    async def get_power(self) -> float | None:
        power = await self._inner.get_power()
        return power if power > 0 else None

    async def get_energy(self) -> float | None:
        return None

    async def get_session(self) -> ChargingSession | None:
        return None

    async def get_meter_values(self) -> MeterValues | None:
        return None

    async def test_connection(self) -> ConnectionTestResult:
        try:
            status = await self.get_status()
            caps = await self.get_capabilities()
            if not status.online:
                return ConnectionTestResult(
                    success=False,
                    status="DEVICE_NOT_FOUND",
                    message="Kunde inte nå laddboxen via Charge Amps API.",
                )
            return ConnectionTestResult(
                success=True,
                status="CONNECTED",
                message="Ansluten via Charge Amps Cloud API.",
                detected_device=DetectedDevice(
                    vendor="Charge Amps",
                    model=self._model_id,
                    serial_number=self._charger_id,
                ),
                capabilities=caps,
            )
        except Exception as exc:
            message = str(exc)
            status = "AUTH_FAILED" if "auth" in message.lower() else "PROTOCOL_ERROR"
            return ConnectionTestResult(success=False, status=status, message=message)


def _normalize(legacy: ChargerStatus) -> NormalizedChargerStatus:
    if not legacy.connected:
        state = "OFFLINE"
    elif legacy.charging:
        state = "CHARGING"
    elif legacy.vehicle_connected:
        state = "CONNECTED"
    else:
        state = "AVAILABLE"
    return NormalizedChargerStatus(
        online=legacy.connected,
        vehicle_connected=legacy.vehicle_connected,
        charging=legacy.charging,
        state=state,
        configured_current_a=legacy.current_limit_a,
        requested_current_a=legacy.current_limit_a,
        timestamp=datetime.now(UTC),
    )
