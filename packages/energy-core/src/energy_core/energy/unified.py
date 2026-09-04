"""Canonical runtime energy state model for EMIC Phase 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class DataFreshness(StrEnum):
    LIVE = "LIVE"
    FRESH = "FRESH"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class ProviderHealthStatus(StrEnum):
    OK = "ok"
    STALE = "stale"
    DEGRADED = "degraded"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SolarSection:
    production_kw: float | None = None
    today_kwh: float | None = None
    forecast_kw: float | None = None
    expected_today_kwh: float | None = None
    remaining_kwh: float | None = None
    confidence_pct: float | None = None


@dataclass(frozen=True, slots=True)
class GridSection:
    import_kw: float | None = None
    export_kw: float | None = None
    import_today_kwh: float | None = None
    export_today_kwh: float | None = None


@dataclass(frozen=True, slots=True)
class BatterySection:
    soc_percent: float | None = None
    charge_kw: float | None = None
    discharge_kw: float | None = None
    capacity_kwh: float | None = None
    available_kwh: float | None = None
    state: str | None = None


@dataclass(frozen=True, slots=True)
class HouseSection:
    consumption_kw: float | None = None
    today_kwh: float | None = None


@dataclass(frozen=True, slots=True)
class EvSection:
    connected: bool | None = None
    charging: bool | None = None
    power_kw: float | None = None
    soc_percent: float | None = None
    target_soc: float | None = None
    departure_time: str | None = None
    state: str | None = None


@dataclass(frozen=True, slots=True)
class SpaSection:
    power_kw: float | None = None
    state: str | None = None


@dataclass(frozen=True, slots=True)
class HvacSection:
    power_kw: float | None = None
    state: str | None = None


@dataclass(frozen=True, slots=True)
class PricesSection:
    import_price_sek_kwh: float | None = None
    export_price_sek_kwh: float | None = None
    import_price_eur_kwh: float | None = None
    current_tier: str | None = None


@dataclass(frozen=True, slots=True)
class WeatherSection:
    temperature_c: float | None = None
    cloud_cover_pct: float | None = None


@dataclass(frozen=True, slots=True)
class ForecastSection:
    solar_kwh_today: float | None = None
    solar_kwh_tomorrow: float | None = None
    load_kw: float | None = None
    price_eur_kwh: float | None = None


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    status: ProviderHealthStatus = ProviderHealthStatus.UNKNOWN
    stale_seconds: float | None = None
    last_success_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class HealthSection:
    heartbeat: ProviderHealth = field(default_factory=ProviderHealth)
    charge_amps: ProviderHealth = field(default_factory=ProviderHealth)
    mercedes: ProviderHealth = field(default_factory=ProviderHealth)
    weather: ProviderHealth = field(default_factory=ProviderHealth)
    spa: ProviderHealth = field(default_factory=ProviderHealth)


@dataclass(frozen=True, slots=True)
class UnifiedEnergyState:
    """Canonical runtime model aggregating all key energy flows and states."""

    site_id: int
    site_slug: str
    timestamp: datetime
    data_freshness: DataFreshness = DataFreshness.UNKNOWN
    age_seconds: float = 0.0
    stale: bool = False

    solar: SolarSection = field(default_factory=SolarSection)
    grid: GridSection = field(default_factory=GridSection)
    battery: BatterySection = field(default_factory=BatterySection)
    house: HouseSection = field(default_factory=HouseSection)
    ev: EvSection = field(default_factory=EvSection)
    spa: SpaSection = field(default_factory=SpaSection)
    hvac: HvacSection = field(default_factory=HvacSection)
    prices: PricesSection = field(default_factory=PricesSection)
    weather: WeatherSection = field(default_factory=WeatherSection)
    forecast: ForecastSection = field(default_factory=ForecastSection)
    health: HealthSection = field(default_factory=HealthSection)
