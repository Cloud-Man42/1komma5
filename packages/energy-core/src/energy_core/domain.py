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
