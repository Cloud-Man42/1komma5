"""Runtime state for vehicle charge sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VehicleSessionRuntimeState:
    last_plugged_in: bool | None = None
    last_charging: bool | None = None
    last_meter_kwh: float | None = None
    last_sample_at: datetime | None = None
    last_soc: float | None = None
