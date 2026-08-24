"""Normalized vehicle inputs for smart charging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class VehicleEnergyRequirement:
    """Remaining energy need derived from vehicle SoC and target."""

    current_soc_percent: float | None
    target_soc_percent: float | None
    required_energy_kwh: float | None
    battery_capacity_kwh: float
    quality: str  # MEASURED | ESTIMATED | UNAVAILABLE

    @property
    def has_need(self) -> bool:
        return self.required_energy_kwh is not None and self.required_energy_kwh > 0.05


@dataclass(frozen=True, slots=True)
class VehicleChargingContext:
    """Trusted vehicle telemetry for a linked charger."""

    vehicle_id: int
    display_name: str
    provider: str
    correlation_confidence: float
    correlation_status: str
    requirement: VehicleEnergyRequirement
    target_soc_fraction: float | None
    departure_time: str | None
    deadline_at: datetime | None
    estimated_complete_at: datetime | None
    is_plugged_in: bool | None
    data_age_seconds: float
    stale: bool
    active: bool
