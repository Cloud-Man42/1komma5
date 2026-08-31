from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    slug: str
    name: str
    timezone: str
    external_system_id: str | None


@dataclass(frozen=True, slots=True)
class RawEnergyReading:
    site_slug: str
    recorded_at: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float
    ev_power_w: float | None = None
    battery_charge_w: float | None = None
    battery_discharge_w: float | None = None
    present_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class NormalizedEnergyReading:
    site_slug: str
    recorded_at: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float
    ev_power_w: float | None = None
    battery_charge_w: float | None = None
    battery_discharge_w: float | None = None
    present_fields: frozenset[str] = frozenset()


CORE_READING_FIELDS = frozenset(
    {
        "solar_production_w",
        "consumption_w",
        "grid_import_w",
        "grid_export_w",
        "battery_soc_pct",
        "battery_power_w",
    }
)


def reading_is_actionable(reading: RawEnergyReading | NormalizedEnergyReading) -> bool:
    """Return True when at least one core measurement came from the provider."""
    if not reading.present_fields:
        return False
    return bool(reading.present_fields & CORE_READING_FIELDS)
