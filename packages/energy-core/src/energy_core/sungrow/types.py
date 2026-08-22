"""Sungrow telemetry domain types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class SungrowDeviceInfo:
    display_name: str = "Sungrow Hybrid Inverter SH10"


@dataclass(frozen=True, slots=True)
class SungrowTelemetrySnapshot:
    recorded_at: datetime
    pv_power_w: float | None
    pv_energy_today_kwh: float | None
    load_power_w: float | None
    grid_import_w: float | None
    grid_export_w: float | None
    battery_charge_w: float | None
    battery_discharge_w: float | None
    battery_soc_pct: float | None
    inverter_status: str | None
    data_age_seconds: float
    fresh: bool
    source: Literal["heartbeat"]
