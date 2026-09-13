"""Data models for multi-site overview."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


DEFAULT_BATTERY_CAPACITY_KWH = 13.5


@dataclass(frozen=True, slots=True)
class SiteOverviewEntry:
    slug: str
    name: str
    timezone: str
    currency: str
    price_area: str
    available: bool
    health: str  # healthy | degraded | offline
    health_detail: str | None
    updated_at: datetime | None
    data_age_seconds: int | None
    is_stale: bool
    solar_power_kw: float | None
    consumption_power_kw: float | None
    grid_import_power_kw: float | None
    grid_export_power_kw: float | None
    battery_soc_percent: float | None
    battery_power_kw: float | None
    battery_capacity_kwh: float | None
    battery_stored_kwh: float | None
    battery_state: str | None
    solar_today_kwh: float | None
    consumption_today_kwh: float | None
    grid_import_today_kwh: float | None
    grid_export_today_kwh: float | None
    battery_charged_today_kwh: float | None
    battery_discharged_today_kwh: float | None
    cost_today: float | None
    savings_today: float | None
    ev_power_kw: float | None
    ev_state: str | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MultiSiteAggregate:
    solar_power_kw: float | None
    consumption_power_kw: float | None
    grid_import_power_kw: float | None
    grid_export_power_kw: float | None
    grid_net_power_kw: float | None
    battery_charge_power_kw: float | None
    battery_discharge_power_kw: float | None
    battery_capacity_kwh: float | None
    battery_stored_kwh: float | None
    battery_soc_percent: float | None
    solar_today_kwh: float | None
    consumption_today_kwh: float | None
    grid_import_today_kwh: float | None
    grid_export_today_kwh: float | None
    battery_charged_today_kwh: float | None
    battery_discharged_today_kwh: float | None
    ev_power_kw: float | None
    self_consumption_percent: float | None
    self_sufficiency_percent: float | None
    best_solar_site_slug: str | None
    best_solar_site_kwh: float | None
    highest_load_site_slug: str | None
    highest_load_site_kw: float | None


@dataclass(frozen=True, slots=True)
class CurrencyAmount:
    currency: str
    cost_today: float | None
    savings_today: float | None


@dataclass(frozen=True, slots=True)
class MultiSiteHealth:
    healthy: int
    degraded: int
    offline: int


@dataclass(frozen=True, slots=True)
class DataQualitySummary:
    partial: bool
    sites_requested: int
    sites_available: int
    sites_stale: int
    message: str | None


@dataclass(frozen=True, slots=True)
class FreshnessSummary:
    freshest_at: datetime | None
    oldest_at: datetime | None
    max_data_age_seconds: int | None


@dataclass(frozen=True, slots=True)
class MultiSiteOverview:
    sites: tuple[SiteOverviewEntry, ...]
    aggregate: MultiSiteAggregate
    health: MultiSiteHealth
    data_quality: DataQualitySummary
    freshness: FreshnessSummary
    currencies: tuple[CurrencyAmount, ...]
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "generatedAt": self.generated_at.isoformat(),
            "sites": [_site_entry_dict(s) for s in self.sites],
            "aggregate": _aggregate_dict(self.aggregate),
            "health": {
                "healthy": self.health.healthy,
                "degraded": self.health.degraded,
                "offline": self.health.offline,
            },
            "dataQuality": {
                "partial": self.data_quality.partial,
                "sitesRequested": self.data_quality.sites_requested,
                "sitesAvailable": self.data_quality.sites_available,
                "sitesStale": self.data_quality.sites_stale,
                "message": self.data_quality.message,
            },
            "freshness": {
                "freshestAt": self.freshness.freshest_at.isoformat() if self.freshness.freshest_at else None,
                "oldestAt": self.freshness.oldest_at.isoformat() if self.freshness.oldest_at else None,
                "maxDataAgeSeconds": self.freshness.max_data_age_seconds,
            },
            "currencies": [
                {"currency": c.currency, "costToday": c.cost_today, "savingsToday": c.savings_today}
                for c in self.currencies
            ],
        }


def _site_entry_dict(s: SiteOverviewEntry) -> dict[str, Any]:
    return {
        "slug": s.slug,
        "name": s.name,
        "timezone": s.timezone,
        "currency": s.currency,
        "priceArea": s.price_area,
        "available": s.available,
        "health": s.health,
        "healthDetail": s.health_detail,
        "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
        "dataAgeSeconds": s.data_age_seconds,
        "isStale": s.is_stale,
        "live": {
            "solarPowerKw": s.solar_power_kw,
            "consumptionPowerKw": s.consumption_power_kw,
            "gridImportPowerKw": s.grid_import_power_kw,
            "gridExportPowerKw": s.grid_export_power_kw,
            "batterySocPercent": s.battery_soc_percent,
            "batteryPowerKw": s.battery_power_kw,
            "batteryCapacityKwh": s.battery_capacity_kwh,
            "batteryStoredKwh": s.battery_stored_kwh,
            "batteryState": s.battery_state,
            "evPowerKw": s.ev_power_kw,
        },
        "today": {
            "solarKwh": s.solar_today_kwh,
            "consumptionKwh": s.consumption_today_kwh,
            "gridImportKwh": s.grid_import_today_kwh,
            "gridExportKwh": s.grid_export_today_kwh,
            "batteryChargedKwh": s.battery_charged_today_kwh,
            "batteryDischargedKwh": s.battery_discharged_today_kwh,
            "costToday": s.cost_today,
            "savingsToday": s.savings_today,
        },
        "evState": s.ev_state,
        "error": s.error,
    }


def _aggregate_dict(a: MultiSiteAggregate) -> dict[str, Any]:
    return {
        "solarPowerKw": a.solar_power_kw,
        "consumptionPowerKw": a.consumption_power_kw,
        "gridImportPowerKw": a.grid_import_power_kw,
        "gridExportPowerKw": a.grid_export_power_kw,
        "gridNetPowerKw": a.grid_net_power_kw,
        "batteryChargePowerKw": a.battery_charge_power_kw,
        "batteryDischargePowerKw": a.battery_discharge_power_kw,
        "batteryCapacityKwh": a.battery_capacity_kwh,
        "batteryStoredKwh": a.battery_stored_kwh,
        "batterySocPercent": a.battery_soc_percent,
        "solarTodayKwh": a.solar_today_kwh,
        "consumptionTodayKwh": a.consumption_today_kwh,
        "gridImportTodayKwh": a.grid_import_today_kwh,
        "gridExportTodayKwh": a.grid_export_today_kwh,
        "batteryChargedTodayKwh": a.battery_charged_today_kwh,
        "batteryDischargedTodayKwh": a.battery_discharged_today_kwh,
        "evPowerKw": a.ev_power_kw,
        "selfConsumptionPercent": a.self_consumption_percent,
        "selfSufficiencyPercent": a.self_sufficiency_percent,
        "bestSolarSiteSlug": a.best_solar_site_slug,
        "bestSolarSiteKwh": a.best_solar_site_kwh,
        "highestLoadSiteSlug": a.highest_load_site_slug,
        "highestLoadSiteKw": a.highest_load_site_kw,
    }
