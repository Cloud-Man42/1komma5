"""Widget API response schemas (camelCase JSON for Apple clients)."""

from __future__ import annotations

from datetime import datetime

from energy_core.energy_state.models import EnergySiteSnapshot
from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class WidgetSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class WidgetSiteRef(WidgetSchema):
    id: str
    name: str


class WidgetSolarSection(WidgetSchema):
    power_kw: float | None = None
    today_kwh: float | None = None


class WidgetHouseSection(WidgetSchema):
    power_kw: float | None = None
    today_kwh: float | None = None


class WidgetBatterySection(WidgetSchema):
    soc_percent: float | None = None
    power_kw: float | None = None
    state: str
    state_text: str | None = None


class WidgetGridSection(WidgetSchema):
    power_kw: float | None = None
    direction: str | None = None
    import_power_kw: float | None = None
    export_power_kw: float | None = None


class WidgetEvSection(WidgetSchema):
    state: str
    state_text: str | None = None
    power_kw: float | None = None
    energy_today_kwh: float | None = None


class WidgetEconomySection(WidgetSchema):
    saved_today_sek: float | None = None
    saved_month_sek: float | None = None
    economic_data_quality: str = "unavailable"


class WidgetSmartChargingSection(WidgetSchema):
    mode: str | None = None
    state: str | None = None
    decision_text: str | None = None


class WidgetEmicSection(WidgetSchema):
    mode: str | None = None
    decision_text: str


class WidgetStatusResponse(WidgetSchema):
    api_version: str = "1.0"
    site: WidgetSiteRef
    solar: WidgetSolarSection
    house: WidgetHouseSection
    battery: WidgetBatterySection
    grid: WidgetGridSection
    ev: WidgetEvSection
    economy: WidgetEconomySection
    smart_charging: WidgetSmartChargingSection | None = None
    emic: WidgetEmicSection
    system_status: str
    updated_at: datetime | None = None
    data_age_seconds: int | None = None
    is_stale: bool = False


class WidgetSiteListItem(WidgetSchema):
    id: str
    name: str
    timezone: str
    system_status: str


class WidgetSitesResponse(WidgetSchema):
    api_version: str = "1.0"
    sites: list[WidgetSiteListItem]


class WidgetSummaryTotals(WidgetSchema):
    solar_power_kw: float | None = None
    house_power_kw: float | None = None
    battery_stored_kwh: float | None = None
    saved_today_sek: float | None = None


class WidgetSummaryResponse(WidgetSchema):
    api_version: str = "1.0"
    sites: list[WidgetStatusResponse]
    totals: WidgetSummaryTotals
    updated_at: datetime | None = None
    data_age_seconds: int | None = None
    is_stale: bool = False


class WidgetMeResponse(WidgetSchema):
    api_version: str = "1.0"
    device_id: int
    owner_label: str
    device_name: str
    device_type: str
    default_site_slug: str | None = None
    scopes: list[str] = Field(default_factory=list)
    last_seen_at: datetime | None = None


def _grid_direction(grid_power_kw: float | None) -> str | None:
    if grid_power_kw is None:
        return None
    if grid_power_kw > 0.001:
        return "import"
    if grid_power_kw < -0.001:
        return "export"
    return "neutral"


def snapshot_to_widget_status(snapshot: EnergySiteSnapshot) -> WidgetStatusResponse:
    smart = None
    if (
        snapshot.smart_charging_mode is not None
        or snapshot.smart_charging_state is not None
        or snapshot.smart_charging_decision_text
    ):
        smart = WidgetSmartChargingSection(
            mode=snapshot.smart_charging_mode.value if snapshot.smart_charging_mode else None,
            state=snapshot.smart_charging_state.value if snapshot.smart_charging_state else None,
            decision_text=snapshot.smart_charging_decision_text,
        )

    return WidgetStatusResponse(
        site=WidgetSiteRef(id=snapshot.site_slug, name=snapshot.site_name),
        solar=WidgetSolarSection(
            power_kw=snapshot.solar_power_kw,
            today_kwh=snapshot.solar_energy_today_kwh,
        ),
        house=WidgetHouseSection(
            power_kw=snapshot.house_power_kw,
            today_kwh=snapshot.house_energy_today_kwh,
        ),
        battery=WidgetBatterySection(
            soc_percent=snapshot.battery_soc_percent,
            power_kw=snapshot.battery_power_kw,
            state=snapshot.battery_state.value,
            state_text=snapshot.battery_state_text_sv,
        ),
        grid=WidgetGridSection(
            power_kw=snapshot.grid_power_kw,
            direction=_grid_direction(snapshot.grid_power_kw),
            import_power_kw=snapshot.grid_import_power_kw,
            export_power_kw=snapshot.grid_export_power_kw,
        ),
        ev=WidgetEvSection(
            state=snapshot.ev_state.value,
            state_text=snapshot.ev_state_text_sv,
            power_kw=snapshot.ev_power_kw,
            energy_today_kwh=snapshot.ev_energy_today_kwh,
        ),
        economy=WidgetEconomySection(
            saved_today_sek=snapshot.saved_today_sek,
            saved_month_sek=snapshot.saved_month_sek,
            economic_data_quality=snapshot.economic_data_quality.value,
        ),
        smart_charging=smart,
        emic=WidgetEmicSection(
            mode=snapshot.operating_mode,
            decision_text=snapshot.decision_text,
        ),
        system_status=snapshot.system_status.value,
        updated_at=snapshot.updated_at,
        data_age_seconds=snapshot.data_age_seconds,
        is_stale=snapshot.is_stale,
    )
