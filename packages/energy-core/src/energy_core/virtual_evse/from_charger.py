"""Build Virtual EVSE state from persisted charger telemetry."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.db.models import EvChargerModel
from energy_core.virtual_evse.state import VirtualEvseState, VirtualEvseStatus


def virtual_evse_state_from_charger(charger: EvChargerModel) -> VirtualEvseState | None:
    if not charger.virtual_evse_enabled:
        return None
    device_id = charger.semp_device_id or f"emic-evse-{charger.id}"
    recorded_at = charger.last_bridge_run_at or charger.last_heartbeat_data_at or datetime.now(UTC)
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)

    power_w = charger.last_actual_power_w
    if power_w is not None and power_w < 0:
        power_w = 0.0
    vehicle_connected = bool(charger.last_vehicle_connected)
    is_charging = bool(power_w and power_w > 0)

    if is_charging:
        status = VirtualEvseStatus.CHARGING
    elif vehicle_connected:
        status = VirtualEvseStatus.FINISHED
    else:
        status = VirtualEvseStatus.IDLE

    stale = False
    if charger.last_bridge_run_at is not None:
        bridge_at = charger.last_bridge_run_at
        if bridge_at.tzinfo is None:
            bridge_at = bridge_at.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - bridge_at.astimezone(UTC)).total_seconds()
        stale = age > float(charger.stale_timeout_seconds)

    return VirtualEvseState(
        device_id=device_id,
        recorded_at=recorded_at,
        status=status,
        reported_power_w=power_w,
        vehicle_connected=vehicle_connected,
        halo_power_w=power_w,
        stale=stale,
        heartbeat_detected=False,
    )
