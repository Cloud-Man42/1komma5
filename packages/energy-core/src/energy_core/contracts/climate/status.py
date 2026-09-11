"""Generic climate device contracts (vendor-neutral)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ClimateSourceQuality = Literal["LIVE", "STALE", "UNAVAILABLE"]


@dataclass(frozen=True, slots=True)
class ClimateDeviceState:
    device_id: str
    site_id: int
    observed_at: datetime
    temperature_c: float | None = None
    humidity_percent: float | None = None
    climate_mode: str | None = None
    target_temperature_c: float | None = None
    online: bool | None = None
    source_quality: ClimateSourceQuality = "LIVE"
    display_name: str | None = None
    vendor: str | None = None
