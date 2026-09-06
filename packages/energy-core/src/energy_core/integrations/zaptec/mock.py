"""Mock Zaptec REST client for tests and ZAPTEC_MOCK mode."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.integrations.zaptec.constants import (
    COMMAND_RESUME_CHARGING,
    COMMAND_STOP_CHARGING_FINAL,
    OPERATION_CHARGING,
    OPERATION_NO_VEHICLE,
    STATE_CHARGE_CURRENT_A,
    STATE_CHARGER_OPERATION_MODE,
    STATE_FINAL_STOP_ACTIVE,
    STATE_IS_ONLINE,
    STATE_SESSION_ENERGY_KWH,
    STATE_TOTAL_CHARGE_POWER_W,
)
from energy_core.integrations.zaptec.parsing import parse_charger_status
from energy_core.integrations.zaptec.types import ZaptecChargerStatus


class ZaptecMockClient:
    def __init__(self, *, charger_id: str, installation_id: str | None = None) -> None:
        self.charger_id = charger_id
        self.installation_id = installation_id
        self._operation_mode = OPERATION_NO_VEHICLE
        self._final_stop_active = 0
        self._charge_current_a = 0.0
        self._power_w = 0.0
        self._available_current_a = 16.0

    async def test_connection(self, charger_id: str) -> ZaptecChargerStatus:
        return await self.get_charger_status(charger_id)

    async def get_charger_status(self, charger_id: str) -> ZaptecChargerStatus:
        _ = charger_id
        now = datetime.now(UTC)
        observations = [
            {"stateId": STATE_IS_ONLINE, "valueAsString": "1", "timestamp": now.isoformat()},
            {
                "stateId": STATE_CHARGER_OPERATION_MODE,
                "valueAsString": str(self._operation_mode),
                "timestamp": now.isoformat(),
            },
            {
                "stateId": STATE_FINAL_STOP_ACTIVE,
                "valueAsString": str(self._final_stop_active),
                "timestamp": now.isoformat(),
            },
            {
                "stateId": STATE_TOTAL_CHARGE_POWER_W,
                "valueAsString": str(int(self._power_w)),
                "timestamp": now.isoformat(),
            },
            {
                "stateId": STATE_SESSION_ENERGY_KWH,
                "valueAsString": "0",
                "timestamp": now.isoformat(),
            },
            {
                "stateId": STATE_CHARGE_CURRENT_A,
                "valueAsString": str(self._charge_current_a),
                "timestamp": now.isoformat(),
            },
        ]
        return parse_charger_status(observations, now=now)

    async def send_charger_command(self, charger_id: str, command_id: int) -> None:
        _ = charger_id
        if command_id == COMMAND_STOP_CHARGING_FINAL:
            self._operation_mode = 5
            self._final_stop_active = 1
            self._power_w = 0.0
            self._charge_current_a = 0.0
            return
        if command_id == COMMAND_RESUME_CHARGING:
            self._operation_mode = OPERATION_CHARGING
            self._final_stop_active = 0
            self._power_w = 7200.0
            self._charge_current_a = min(self._available_current_a, 16.0)
            return
        raise NotImplementedError(f"Mock Zaptec client does not support command {command_id}")

    async def stop_charging(self, charger_id: str) -> None:
        await self.send_charger_command(charger_id, COMMAND_STOP_CHARGING_FINAL)

    async def resume_charging(self, charger_id: str) -> None:
        await self.send_charger_command(charger_id, COMMAND_RESUME_CHARGING)

    async def set_installation_available_current(
        self,
        installation_id: str,
        *,
        available_current_a: float,
    ) -> None:
        _ = installation_id
        self._available_current_a = available_current_a
        if available_current_a <= 0:
            self._operation_mode = 5
            self._final_stop_active = 1
            self._power_w = 0.0
            self._charge_current_a = 0.0
        elif self._operation_mode == OPERATION_CHARGING:
            self._charge_current_a = min(available_current_a, 16.0)
