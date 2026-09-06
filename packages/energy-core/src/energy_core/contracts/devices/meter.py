"""Vendor-neutral meter reading types and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class IMeterReader(Protocol):
    async def get_snapshot(self) -> MeterSnapshot: ...


@dataclass(frozen=True, slots=True)
class MeterSnapshot:
    """Point-in-time charger meter reading."""

    recorded_at: datetime
    cumulative_kwh: float | None
    power_w: float | None
    configured_current_a: float | None
    actual_charging_current_a: float | None
    is_charging: bool
    vehicle_connected: bool
    ocpp_status: str
    phase_current_l1_a: float | None
    phase_current_l2_a: float | None
    phase_current_l3_a: float | None
    energy_source: str  # meter | power_estimate | unavailable


def session_energy_from_meter(start_kwh: float | None, stop_kwh: float | None) -> tuple[float | None, str]:
    """Return (session_kwh, quality) from cumulative meter delta."""
    if start_kwh is None or stop_kwh is None:
        return None, "INCOMPLETE"
    delta = stop_kwh - start_kwh
    if delta < 0:
        return None, "INCOMPLETE"
    if delta == 0:
        return 0.0, "MEASURED"
    return round(delta, 4), "MEASURED"


def integrate_power_kwh(power_w: float, duration_hours: float) -> float:
    if power_w <= 0 or duration_hours <= 0:
        return 0.0
    return round(power_w * duration_hours / 1000.0, 4)
