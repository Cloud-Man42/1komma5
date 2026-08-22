"""Bridge vendor-neutral adapters to legacy smart-charging control surface."""

from __future__ import annotations

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.framework.models import ChargerAdapter


class LegacyControlBridge:
    """Expose legacy control methods expected by SmartChargingEngine."""

    def __init__(self, adapter: ChargerAdapter) -> None:
        self._adapter = adapter

    async def get_status(self) -> ChargerStatus:
        return await self._adapter.get_legacy_status()

    async def set_current(self, amps: float) -> None:
        await self._adapter.set_max_current(amps)

    async def set_current_limit(self, amps: float) -> None:
        await self._adapter.set_max_current(amps)

    async def start_charging(self) -> None:
        await self._adapter.start_charging()

    async def stop_charging(self) -> None:
        await self._adapter.stop_charging()

    async def get_capabilities(self):
        return await self._adapter.get_capabilities()

    async def get_current(self) -> float:
        current = await self._adapter.get_requested_current()
        return current or 0.0

    async def get_power(self) -> float:
        return (await self._adapter.get_power()) or 0.0

    async def is_connected(self) -> bool:
        status = await self.get_status()
        return status.connected

    async def is_vehicle_connected(self) -> bool:
        status = await self.get_status()
        return status.vehicle_connected

    async def test_connection(self):
        return await self._adapter.test_connection()
