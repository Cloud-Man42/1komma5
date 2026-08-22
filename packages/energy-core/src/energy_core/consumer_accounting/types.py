"""Generic energy consumer accounting types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class EnergyConsumerType(StrEnum):
    HOUSE = "HOUSE"
    EV = "EV"
    SPA = "SPA"
    HEAT_PUMP = "HEAT_PUMP"
    SERVER = "SERVER"
    OTHER = "OTHER"


class DataQuality(StrEnum):
    MEASURED = "MEASURED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class SpaEnergySample:
    power_w: float
    energy_delta_wh: float
    heater_active: bool
    pump_states: dict[str, str]
    water_temperature_c: float | None
    set_temperature_c: float | None
    source: str
    quality: DataQuality
    component_breakdown: dict[str, float] = field(default_factory=dict)
    recorded_at: datetime | None = None

    @property
    def energy_delta_kwh(self) -> float:
        return self.energy_delta_wh / 1000.0
