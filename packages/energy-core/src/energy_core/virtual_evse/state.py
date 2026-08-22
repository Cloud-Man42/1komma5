"""Virtual EVSE state for SEMP reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class VirtualEvseStatus(StrEnum):
    IDLE = "Idle"
    CHARGING = "Charging"
    FINISHED = "Finished"


@dataclass(frozen=True, slots=True)
class VirtualEvseState:
    device_id: str
    recorded_at: datetime
    status: VirtualEvseStatus
    reported_power_w: float | None
    vehicle_connected: bool
    halo_power_w: float | None
    stale: bool
    heartbeat_detected: bool
