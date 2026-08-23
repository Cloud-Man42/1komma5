"""Mock Charge Amps Halo controller for dev/test."""

from __future__ import annotations

import logging

from energy_core.chargers.base import ChargerStatus

logger = logging.getLogger(__name__)


class MockChargeAmpsController:
    def __init__(
        self, charger_id: str, *, connected: bool = True, vehicle_connected: bool = True
    ) -> None:
        self.charger_id = charger_id
        self._connected = connected
        self._vehicle_connected = vehicle_connected
        self._current_limit_a: float = 0.0
        self._charging = False

    async def get_status(self) -> ChargerStatus:
        return ChargerStatus(
            connected=self._connected,
            vehicle_connected=self._vehicle_connected,
            current_limit_a=self._current_limit_a,
            charging=self._charging,
        )

    async def set_current_limit(self, amps: float) -> None:
        self._current_limit_a = max(0.0, amps)
        self._charging = self._current_limit_a > 0 and self._vehicle_connected
        logger.info(
            "mock_chargeamps charger_id=%s set_current_limit_a=%.1f charging=%s",
            self.charger_id,
            self._current_limit_a,
            self._charging,
        )

    async def start_charging(self) -> None:
        if self._vehicle_connected and self._current_limit_a > 0:
            self._charging = True

    async def stop_charging(self) -> None:
        self._current_limit_a = 0.0
        self._charging = False

    async def is_connected(self) -> bool:
        return self._connected

    async def is_vehicle_connected(self) -> bool:
        return self._vehicle_connected
