"""Schemas for Raspberry Pi display overview API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DisplaySectionMeta(BaseModel):
    available: bool = True
    unavailable_reason: str | None = None
    stale: bool = False


class DisplaySiteSection(BaseModel):
    slug: str
    name: str
    timezone: str


class DisplayFreshnessSection(BaseModel):
    updated_at: datetime | None = None
    data_age_seconds: int | None = None
    stale: bool = False
    connection_state: str = "CONNECTED"


class DisplaySparklinePoint(BaseModel):
    timestamp: datetime
    value: float


class DisplaySparklineSeries(BaseModel):
    points: list[DisplaySparklinePoint] = Field(default_factory=list)


class DisplayLiveMetrics(BaseModel):
    solar_power_kw: float | None = None
    house_power_kw: float | None = None
    grid_net_power_kw: float | None = None
    grid_direction: str | None = None
    grid_direction_sv: str | None = None
    battery_soc_pct: float | None = None
    battery_power_kw: float | None = None
    battery_state_sv: str | None = None
    battery_stored_kwh: float | None = None
    battery_capacity_kwh: float | None = None
    solar_surplus_kw: float | None = None
    produced_today_kwh: float | None = None
    consumed_today_kwh: float | None = None
    imported_today_kwh: float | None = None
    exported_today_kwh: float | None = None
    self_consumption_pct: float | None = None
    self_sufficiency_pct: float | None = None
    battery_soh_pct: float | None = None


class DisplayWeatherSection(DisplaySectionMeta):
    temperature_c: float | None = None
    label_sv: str | None = None
    icon: str | None = None


class DisplayPriceSection(DisplaySectionMeta):
    tier: str | None = None
    tier_label_sv: str | None = None
    current_ore_kwh: float | None = None


class DisplayVehicleSection(DisplaySectionMeta):
    display_name: str | None = None
    model: str | None = None
    status_sv: str | None = None
    soc_pct: float | None = None
    range_km: float | None = None
    charging_mode_sv: str | None = None
    ready_by: datetime | None = None
    cost_today_sek: float | None = None


class DisplayChargerSection(DisplaySectionMeta):
    name: str | None = None
    status_sv: str | None = None
    power_w: float | None = None
    available_current_a: float | None = None
    smart_charging_active: bool | None = None
    ready_by: datetime | None = None
    price_tier_label_sv: str | None = None


class DisplaySpaSection(DisplaySectionMeta):
    water_temperature_c: float | None = None
    filter_status_sv: str | None = None
    next_cleaning_at: datetime | None = None
    consumption_today_kwh: float | None = None
    cost_today_sek: float | None = None
    power_w: float | None = None


class DisplayEconomyDayPoint(BaseModel):
    day: int
    savings_sek: float
    cost_sek: float
    net_sek: float


class DisplayEconomySection(DisplaySectionMeta):
    total_savings_sek: float | None = None
    total_savings_change_pct: float | None = None
    total_cost_sek: float | None = None
    total_cost_change_pct: float | None = None
    net_sek: float | None = None
    net_change_pct: float | None = None
    daily: list[DisplayEconomyDayPoint] = Field(default_factory=list)


class DisplayHighlightItem(BaseModel):
    label_sv: str
    value: str
    detail_sv: str | None = None


class DisplayHighlightsSection(DisplaySectionMeta):
    items: list[DisplayHighlightItem] = Field(default_factory=list)


class DisplayFlowNode(BaseModel):
    key: str
    label_sv: str
    power_kw: float | None = None
    status_sv: str | None = None


class DisplayFlowSection(DisplaySectionMeta):
    nodes: list[DisplayFlowNode] = Field(default_factory=list)


class DisplaySystemStatusSection(BaseModel):
    status_sv: str = "Allt normalt"
    detail_sv: str = "Alla system fungerar som de ska."
    healthy: bool = True


class DisplayOverviewResponse(BaseModel):
    generated_at: datetime
    site: DisplaySiteSection
    freshness: DisplayFreshnessSection
    live: DisplayLiveMetrics
    sparklines: dict[str, DisplaySparklineSeries] = Field(default_factory=dict)
    weather: DisplayWeatherSection
    price: DisplayPriceSection
    flow: DisplayFlowSection
    vehicle: DisplayVehicleSection
    charger: DisplayChargerSection
    spa: DisplaySpaSection
    economy: DisplayEconomySection
    highlights: DisplayHighlightsSection
    system_status: DisplaySystemStatusSection
