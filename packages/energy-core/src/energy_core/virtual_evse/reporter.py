"""Map Halo meter readings to Virtual EVSE SEMP state."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.virtual_evse.device_profile import VirtualEvseDeviceProfile
from energy_core.virtual_evse.state import VirtualEvseState, VirtualEvseStatus


def meter_to_virtual_evse_state(
    profile: VirtualEvseDeviceProfile,
    meter: MeterSnapshot,
    *,
    stale_timeout_seconds: float = 120.0,
    heartbeat_ev_power_w: float | None = None,
    now: datetime | None = None,
) -> VirtualEvseState:
    now = now or datetime.now(UTC)
    recorded_at = meter.recorded_at
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    age = max(0.0, (now - recorded_at).total_seconds())
    stale = age > stale_timeout_seconds

    power_w = meter.power_w
    if power_w is not None and power_w < 0:
        power_w = 0.0

    if meter.is_charging and power_w and power_w > 0:
        status = VirtualEvseStatus.CHARGING
    elif meter.vehicle_connected and not meter.is_charging:
        status = VirtualEvseStatus.FINISHED
    else:
        status = VirtualEvseStatus.IDLE

    heartbeat_detected = heartbeat_ev_power_w is not None

    return VirtualEvseState(
        device_id=profile.device_id,
        recorded_at=recorded_at,
        status=status,
        reported_power_w=power_w,
        vehicle_connected=meter.vehicle_connected,
        halo_power_w=power_w,
        stale=stale,
        heartbeat_detected=heartbeat_detected,
    )
