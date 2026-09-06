"""Parsed Zaptec charger telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ZaptecChargerStatus:
    online: bool
    vehicle_connected: bool
    charging: bool
    state: str
    power_w: float | None
    session_energy_kwh: float | None
    charge_current_a: float | None
    timestamp: datetime
