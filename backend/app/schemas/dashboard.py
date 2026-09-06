from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class DashboardSectionMeta(BaseModel):
    unavailable_reason: str | None = None


class DashboardSiteSection(BaseModel):
    slug: str
    name: str
    timezone: str


class DashboardFreshnessSection(BaseModel):
    updated_at: datetime | None = None
    data_age_seconds: int | None = None
    stale: bool = False


class DashboardLiveSection(DashboardSectionMeta):
    solar_production_w: float | None = None
    consumption_w: float | None = None
    grid_import_w: float | None = None
    grid_export_w: float | None = None
    battery_soc_pct: float | None = None
    battery_power_w: float | None = None
    battery_direction: str | None = None
    ev_power_w: float | None = None


class DashboardTodaySection(DashboardSectionMeta):
    produced_kwh: float | None = None
    consumed_kwh: float | None = None
    imported_kwh: float | None = None
    exported_kwh: float | None = None
    energy_cost_sek: float | None = None
    savings_sek: float | None = None
    produced_kwh_yesterday: float | None = None
    consumed_kwh_yesterday: float | None = None
    imported_kwh_yesterday: float | None = None
    exported_kwh_yesterday: float | None = None
    energy_cost_sek_yesterday: float | None = None
    savings_sek_yesterday: float | None = None


class DashboardEvSection(DashboardSectionMeta):
    available: bool = False
    charging: bool = False
    charging_mode: str | None = None
    display_status_sv: str | None = None
    power_w: float | None = None
    session_energy_kwh: float | None = None
    solar_share_pct: float | None = None
    estimated_cost_sek: float | None = None
    next_planned_charge_at: datetime | None = None


class DashboardSolarSection(DashboardSectionMeta):
    expected_today_kwh: float | None = None
    remaining_kwh: float | None = None
    peak_power_w: float | None = None
    peak_at: datetime | None = None
    confidence_pct: float | None = None
    inverter_max_power_kw: float | None = None


class DashboardPriceSection(DashboardSectionMeta):
    current_eur_kwh: float | None = None
    lowest_eur_kwh: float | None = None
    highest_eur_kwh: float | None = None
    tier: str | None = None


class DashboardOptimizationSection(DashboardSectionMeta):
    strategy_sv: str | None = None
    explanation_sv: str | None = None
    reasoning_steps: list[str] = Field(default_factory=list)
    solar_first: bool | None = None
    battery_soc_pct: float | None = None


class DashboardVehicleSection(DashboardSectionMeta):
    available: bool = False
    display_name: str | None = None
    mode: str = "parked"
    state_of_charge_percent: float | None = None
    electric_range_km: float | None = None
    is_plugged_in: bool | None = None
    is_charging: bool | None = None
    charging_power_kw: float | None = None
    location_name: str | None = None
    charging_type: str | None = None
    session_energy_kwh: float | None = None
    data_quality: str | None = None
    freshness_label: str | None = None


class DashboardAlert(BaseModel):
    severity: str
    message_sv: str


class DashboardResponse(BaseModel):
    site: DashboardSiteSection
    freshness: DashboardFreshnessSection
    live: DashboardLiveSection | None = None
    today: DashboardTodaySection | None = None
    ev: DashboardEvSection | None = None
    vehicle: DashboardVehicleSection | None = None
    solar: DashboardSolarSection | None = None
    price: DashboardPriceSection | None = None
    optimization: DashboardOptimizationSection | None = None
    alerts: list[DashboardAlert] = Field(default_factory=list)
    spa_integration_enabled: bool = False
    vehicle_integration_enabled: bool = False
