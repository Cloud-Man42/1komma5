"""Parse Zaptec charger state observations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.integrations.zaptec.constants import (
    OPERATION_CHARGING,
    OPERATION_FINISHED,
    OPERATION_NO_VEHICLE,
    OPERATION_REQUESTING,
    STATE_CHARGE_CURRENT_A,
    STATE_CHARGER_OPERATION_MODE,
    STATE_IS_ONLINE,
    STATE_SESSION_ENERGY_KWH,
    STATE_TOTAL_CHARGE_POWER_W,
)
from energy_core.integrations.zaptec.types import ZaptecChargerStatus


def _state_map(observations: list[dict[str, Any]]) -> dict[int, str]:
    mapped: dict[int, str] = {}
    for row in observations:
        state_id = row.get("stateId")
        if state_id is None:
            continue
        value = row.get("valueAsString")
        mapped[int(state_id)] = "" if value is None else str(value)
    return mapped


def _float_value(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _operation_label(mode: int | None) -> tuple[bool, bool, str]:
    if mode == OPERATION_CHARGING:
        return True, True, "Charging"
    if mode == OPERATION_REQUESTING:
        return True, False, "Connected"
    if mode == OPERATION_FINISHED:
        return True, False, "Finished"
    if mode == OPERATION_NO_VEHICLE:
        return False, False, "Available"
    return False, False, "Unknown"


def parse_charger_status(observations: list[dict[str, Any]], *, now: datetime | None = None) -> ZaptecChargerStatus:
    states = _state_map(observations)
    now = now or datetime.now(UTC)
    online = states.get(STATE_IS_ONLINE, "1") != "0"
    operation_mode = int(states[STATE_CHARGER_OPERATION_MODE]) if STATE_CHARGER_OPERATION_MODE in states else None
    vehicle_connected, charging, state = _operation_label(operation_mode)
    power_w = _float_value(states.get(STATE_TOTAL_CHARGE_POWER_W))
    session_energy_kwh = _float_value(states.get(STATE_SESSION_ENERGY_KWH))
    charge_current_a = _float_value(states.get(STATE_CHARGE_CURRENT_A))
    return ZaptecChargerStatus(
        online=online,
        vehicle_connected=vehicle_connected,
        charging=charging,
        state=state,
        power_w=power_w,
        session_energy_kwh=session_energy_kwh,
        charge_current_a=charge_current_a,
        timestamp=now,
    )
