"""Aggregated overview builder for Raspberry Pi display."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.api.dashboard import (
    STALE_SECONDS,
    _compute_ev,
    _compute_price,
    _compute_today,
)
from app.schemas_display import (
    DisplayChargerSection,
    DisplayEconomyDayPoint,
    DisplayEconomySection,
    DisplayFlowNode,
    DisplayFlowSection,
    DisplayFreshnessSection,
    DisplayHighlightItem,
    DisplayHighlightsSection,
    DisplayLiveMetrics,
    DisplayOverviewResponse,
    DisplayPriceSection,
    DisplaySiteSection,
    DisplaySparklinePoint,
    DisplaySparklineSeries,
    DisplaySpaSection,
    DisplaySystemStatusSection,
    DisplayVehicleSection,
    DisplayWeatherSection,
)
from energy_core.config import Settings
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EnergyReadingModel
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.db.solar_forecast_repo import SolarSiteConfigRepository
from energy_core.db.vehicle_repo import VehicleRepository
from energy_core.energy_state.service import EnergyStateService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_OVERVIEW_CACHE: dict[str, tuple[float, DisplayOverviewResponse]] = {}
_OVERVIEW_TTL_SECONDS = 3.0
_WEATHER_CACHE: dict[str, tuple[float, DisplayWeatherSection]] = {}
_WEATHER_TTL_SECONDS = 60.0

_TIER_LABELS = {
    "green": "Grönt (billigt)",
    "normal": "Normalt",
    "red": "Rött (dyrt)",
}

_DEFAULT_BATTERY_CAPACITY_KWH = 13.5

# Grid flow below this is neither import nor export.
_GRID_IDLE_KW = 0.025
_GRID_DIRECTION_SV = {"export": "Exporterar", "import": "Importerar", "idle": "Balanserat"}


def _grid_direction(export_kw: float, import_kw: float) -> str:
    if export_kw >= _GRID_IDLE_KW:
        return "export"
    if import_kw >= _GRID_IDLE_KW:
        return "import"
    return "idle"


def _tier_label(tier: str | None) -> str | None:
    if tier is None:
        return None
    return _TIER_LABELS.get(tier, tier)


def _ore_from_eur(eur_kwh: float | None) -> float | None:
    if eur_kwh is None:
        return None
    return round(eur_kwh * 100, 1)


async def _sparklines_for_today(
    session: AsyncSession,
    site,
    settings: Settings,
) -> dict[str, DisplaySparklineSeries]:
    zone = ZoneInfo(site.timezone)
    now_local = datetime.now(zone)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(UTC)
    now_utc = now_local.astimezone(UTC)

    stmt = (
        select(
            EnergyReadingModel.recorded_at,
            EnergyReadingModel.solar_production_w,
            EnergyReadingModel.consumption_w,
            EnergyReadingModel.grid_import_w,
            EnergyReadingModel.grid_export_w,
            EnergyReadingModel.battery_soc_pct,
        )
        .where(
            EnergyReadingModel.site_id == site.id,
            EnergyReadingModel.recorded_at >= start_utc,
            EnergyReadingModel.recorded_at <= now_utc,
        )
        .order_by(EnergyReadingModel.recorded_at)
    )
    rows = (await session.execute(stmt)).all()
    if len(rows) < 2:
        return {}

    bucket_ms = 15 * 60 * 1000
    buckets: dict[int, dict[str, list[float]]] = {}

    def add(bucket_start: int, key: str, value: float) -> None:
        buckets.setdefault(bucket_start, {}).setdefault(key, []).append(value)

    for row in rows:
        ts = row.recorded_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        bucket_start = int(ts.timestamp() * 1000 // bucket_ms * bucket_ms)
        add(bucket_start, "solar", float(row.solar_production_w or 0))
        add(bucket_start, "house", float(row.consumption_w or 0))
        add(bucket_start, "grid", float((row.grid_export_w or 0) - (row.grid_import_w or 0)))
        if row.battery_soc_pct is not None:
            add(bucket_start, "battery", float(row.battery_soc_pct))

    def series(key: str) -> DisplaySparklineSeries:
        points: list[DisplaySparklinePoint] = []
        for bucket_start in sorted(buckets):
            values = buckets[bucket_start].get(key)
            if not values:
                continue
            avg = sum(values) / len(values)
            points.append(
                DisplaySparklinePoint(
                    timestamp=datetime.fromtimestamp(bucket_start / 1000, tz=UTC),
                    value=round(avg, 2),
                )
            )
        return DisplaySparklineSeries(points=points)

    return {
        "solar": series("solar"),
        "house": series("house"),
        "grid": series("grid"),
        "battery": series("battery"),
    }


async def _weather_section(
    session: AsyncSession,
    site,
    settings: Settings,
) -> DisplayWeatherSection:
    cached = _WEATHER_CACHE.get(site.slug)
    if cached is not None and time.monotonic() - cached[0] <= _WEATHER_TTL_SECONDS:
        return cached[1]

    section = DisplayWeatherSection(available=False, unavailable_reason="Väderdata saknas")
    config_repo = SolarSiteConfigRepository(session)
    config = await config_repo.get(site.id, timezone=site.timezone)
    if config is None or not config.enabled or config.latitude is None or config.longitude is None:
        _WEATHER_CACHE[site.slug] = (time.monotonic(), section)
        return section

    try:
        from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
        from energy_core.solar_forecast.weather_conditions import build_current_weather

        coordinator = SolarForecastCoordinator(settings)
        resolved = await coordinator.resolve_weather(session, site, now=datetime.now(UTC))
        if resolved is not None:
            weather, _, _ = resolved
            current = build_current_weather(weather, now=datetime.now(UTC))
            if current is not None:
                section = DisplayWeatherSection(
                    available=True,
                    temperature_c=current.temperature_c,
                    label_sv=current.condition_sv,
                    icon=current.condition_icon,
                )
    except Exception as exc:  # noqa: BLE001 - weather must never break the display
        logger.warning("display weather unavailable for %s: %s", site.slug, exc)

    _WEATHER_CACHE[site.slug] = (time.monotonic(), section)
    return section


async def _next_spa_cleaning_at(session: AsyncSession, site_id: int) -> datetime | None:
    """Next planned filter-cycle start, reusing the spa cleaning planner."""
    try:
        from energy_core.db.flexible_load_plan_repo import FlexibleLoadPlanRepository
        from energy_core.spa_energy.filter_cycle_tracker import next_upcoming_window

        plan = await FlexibleLoadPlanRepository(session).get_latest_for_site(site_id)
        if plan is None:
            return None
        now = datetime.now(UTC)
        window = next_upcoming_window(tuple(plan.windows), now)
        if window is not None:
            return window.start
        # A stale plan whose windows have all passed must render as `--` rather
        # than advertise a cleaning time that is already in the past.
        if plan.window_start is not None and plan.window_start > now:
            return plan.window_start
        return None
    except Exception:
        return None


async def _spa_section(session: AsyncSession, slug: str, enabled: bool) -> DisplaySpaSection:
    if not enabled:
        return DisplaySpaSection(available=False, unavailable_reason="Spa-integration är inte aktiverad")

    try:
        from app.api.spa import _get_spa_context, _period_energy_totals, _period_range

        site, consumer, config = await _get_spa_context(session, slug)
        if not config.integration_enabled:
            return DisplaySpaSection(available=False, unavailable_reason="Spa-integration är avstängd")

        from energy_core.db.consumer_repo import ConsumerSampleRepository
        from energy_core.integrations.arctic_spa.models import ArcticSpaStatus
        from energy_core.integrations.arctic_spa.operational_state import (
            filter_cycle_active,
            filter_status_sv,
        )

        sample_repo = ConsumerSampleRepository(session)
        latest = await sample_repo.get_latest(consumer.id)
        status_payload = {}
        if config.last_status_json:
            try:
                status_payload = json.loads(config.last_status_json)
            except json.JSONDecodeError:
                status_payload = {}
        parsed = ArcticSpaStatus.from_api(status_payload) if status_payload else None

        filter_status = parsed.filter_status if parsed else (latest.filter_status if latest else None)
        filter_sv = "Pågår" if filter_cycle_active(
            filter_status=filter_status,
            current_power_w=latest.power_w if latest else None,
            breakdown={},
        ) else (filter_status_sv(filter_status) or "Data saknas")

        next_cleaning_at = await _next_spa_cleaning_at(session, site.id)

        start, end, _gran = _period_range("today", consumer.timezone or site.timezone)
        totals = await _period_energy_totals(
            session,
            consumer.id,
            start=start,
            end=end,
            fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            site=site,
        )

        return DisplaySpaSection(
            available=True,
            water_temperature_c=parsed.temperature_c if parsed else (latest.water_temperature_c if latest else None),
            filter_status_sv=filter_sv,
            next_cleaning_at=next_cleaning_at,
            consumption_today_kwh=round(totals.get("energy_kwh", 0.0), 1) if totals.get("energy_kwh") else None,
            cost_today_sek=round(totals.get("actual_cost_sek", 0.0), 2) if totals.get("actual_cost_sek") else None,
            power_w=latest.power_w if latest else None,
            stale=latest is None,
        )
    except Exception:
        return DisplaySpaSection(available=False, unavailable_reason="Spa-data kunde inte hämtas")


async def _vehicle_section(
    session: AsyncSession,
    site_id: int,
    enabled: bool,
    ev_section=None,
) -> DisplayVehicleSection:
    if not enabled:
        return DisplayVehicleSection(available=False, unavailable_reason="Fordon-integration är inte aktiverad")

    repo = VehicleRepository(session)
    vehicles = await repo.list_for_site(site_id)
    if not vehicles:
        return DisplayVehicleSection(available=False, unavailable_reason="Inget fordon registrerat")

    vehicle = vehicles[0]
    latest = await repo.get_latest_state(vehicle.id)
    status_sv = "Väntar på bil"
    if latest is not None:
        if latest.is_charging:
            status_sv = "Laddar"
        elif latest.is_plugged_in:
            status_sv = "Ansluten"
        elif latest.connection_state == "CONNECTED":
            status_sv = "Väntar på bil"

    return DisplayVehicleSection(
        available=True,
        display_name=vehicle.display_name,
        model=vehicle.model,
        status_sv=status_sv,
        soc_pct=latest.state_of_charge_percent if latest else None,
        range_km=latest.electric_range_km if latest else None,
        charging_mode_sv="Smart laddning",
        ready_by=ev_section.next_planned_charge_at if ev_section else None,
        cost_today_sek=0.0 if latest and not latest.is_charging else None,
        stale=latest is None,
    )


async def _charger_section(
    session: AsyncSession,
    site,
    settings: Settings,
    ev_section,
    price_tier: str | None,
) -> DisplayChargerSection:
    repo = EvChargerRepository(session)
    chargers = await repo.list_for_site(site.id)
    if not chargers:
        return DisplayChargerSection(available=False, unavailable_reason="Ingen laddbox konfigurerad")

    charger = next((item for item in chargers if item.bridge_enabled), chargers[0])
    status_sv = ev_section.display_status_sv if ev_section and ev_section.display_status_sv else "Väntar på bil"
    return DisplayChargerSection(
        available=True,
        name=charger.name or "Charge Amps Halo",
        status_sv=status_sv,
        power_w=ev_section.power_w if ev_section else charger.last_actual_power_w,
        available_current_a=charger.last_actual_charging_current_a or charger.max_current_a,
        smart_charging_active=bool(charger.bridge_enabled),
        ready_by=ev_section.next_planned_charge_at if ev_section else None,
        price_tier_label_sv=_tier_label(price_tier),
    )


def _change_pct(current: float, previous: float) -> float | None:
    """Percentage change, or None when there is no comparable baseline.

    Returning None keeps the kiosk showing `--` instead of a meaningless
    percentage for the first month of data.
    """
    if abs(previous) < 1e-6:
        return None
    return round((current - previous) / abs(previous) * 100.0, 1)


async def _economy_section(
    session: AsyncSession,
    site,
    settings: Settings,
) -> DisplayEconomySection:
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    zone = ZoneInfo(site.timezone)
    now_local = datetime.now(zone)
    month_start = datetime(now_local.year, now_local.month, 1, tzinfo=zone)

    async def month_stats(start: datetime, end: datetime):
        return await reading_repo.list_financial_stats(
            site_id=site.id,
            period="day",
            timezone=site.timezone,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
            from_time=start.astimezone(UTC),
            to_time=end.astimezone(UTC),
            sell_config=sell_price_config_from_site(site),
        )

    stats = await month_stats(month_start, now_local + timedelta(seconds=1))
    if not stats:
        return DisplayEconomySection(available=False, unavailable_reason="Ekonomidata saknas")

    savings = sum(row.solar_savings_sek + row.battery_savings_sek for row in stats)
    cost = sum(row.grid_import_cost_sek - row.export_revenue_sek for row in stats)
    net = savings - cost

    # Month-over-month deltas, compared against the same number of elapsed days
    # so an in-progress month is not measured against a full one.
    prev_end = month_start
    prev_start = datetime(
        month_start.year if month_start.month > 1 else month_start.year - 1,
        month_start.month - 1 if month_start.month > 1 else 12,
        1,
        tzinfo=zone,
    )
    elapsed = min(now_local - month_start, prev_end - prev_start)
    prev_stats = await month_stats(prev_start, prev_start + elapsed)

    prev_savings = sum(row.solar_savings_sek + row.battery_savings_sek for row in prev_stats)
    prev_cost = sum(row.grid_import_cost_sek - row.export_revenue_sek for row in prev_stats)

    daily: list[DisplayEconomyDayPoint] = []
    for row in stats:
        try:
            day = int(row.period_start.split("-")[-1])
        except (ValueError, AttributeError):
            continue
        row_cost = row.grid_import_cost_sek - row.export_revenue_sek
        row_savings = row.solar_savings_sek + row.battery_savings_sek
        daily.append(
            DisplayEconomyDayPoint(
                day=day,
                savings_sek=round(row_savings, 0),
                cost_sek=round(row_cost, 0),
                net_sek=round(row_savings - row_cost, 0),
            )
        )

    return DisplayEconomySection(
        available=True,
        total_savings_sek=round(savings, 0),
        total_savings_change_pct=_change_pct(savings, prev_savings),
        total_cost_sek=round(cost, 0),
        total_cost_change_pct=_change_pct(cost, prev_cost),
        net_sek=round(net, 0),
        net_change_pct=_change_pct(net, prev_savings - prev_cost),
        daily=daily,
    )


async def _highlights_section(
    session: AsyncSession,
    site,
    settings: Settings,
    produced_kwh: float | None,
    exported_kwh: float | None,
    snapshot,
) -> DisplayHighlightsSection:
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    zone = ZoneInfo(site.timezone)
    now_local = datetime.now(zone)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    peaks = await reading_repo.list_peaks(
        site_id=site.id,
        period="day",
        timezone=site.timezone,
        from_time=start_local.astimezone(UTC),
        to_time=now_local.astimezone(UTC) + timedelta(seconds=1),
    )
    peak_label = "--"
    peak_detail = None
    if peaks:
        solar_peak = max(peaks, key=lambda p: p.solar_production_w)
        peak_label = f"{solar_peak.solar_production_w / 1000:.1f} kW"
        if solar_peak.period_start:
            peak_detail = now_local.strftime("%H:%M")

    battery_charged = snapshot.battery_energy_charged_today_kwh if snapshot else None
    self_use = produced_kwh
    if produced_kwh is not None and exported_kwh is not None:
        self_use = max(0.0, produced_kwh - exported_kwh)
    co2_kg = round(self_use * 0.4, 1) if self_use is not None else None

    items = [
        DisplayHighlightItem(
            label_sv="Högsta soleffekt",
            value=peak_label,
            detail_sv=peak_detail,
        ),
        DisplayHighlightItem(
            label_sv="Batteri laddat från sol",
            value=f"{battery_charged:.1f} kWh" if battery_charged is not None else "--",
        ),
        DisplayHighlightItem(
            label_sv="Export till nätet",
            value=f"{exported_kwh:.1f} kWh" if exported_kwh is not None else "--",
        ),
        DisplayHighlightItem(
            label_sv="Smart laddning aktiv",
            value="0 sek.",
        ),
        DisplayHighlightItem(
            label_sv="CO₂ besparing",
            value=f"{co2_kg:.1f} kg" if co2_kg is not None else "--",
        ),
    ]
    return DisplayHighlightsSection(available=True, items=items)


def _flow_section(live, ev_power_w: float | None, spa_power_w: float | None) -> DisplayFlowSection:
    if live is None:
        return DisplayFlowSection(available=False, unavailable_reason="Live-data saknas")

    solar_kw = (live.solar_production_w or 0) / 1000
    house_kw = (live.consumption_w or 0) / 1000
    battery_kw = abs(live.battery_power_w or 0) / 1000
    grid_export = (live.grid_export_w or 0) / 1000
    grid_import = (live.grid_import_w or 0) / 1000
    grid_kw = grid_export if grid_export >= _GRID_IDLE_KW else grid_import
    grid_dir = _GRID_DIRECTION_SV[_grid_direction(grid_export, grid_import)]

    battery_dir = "Laddar" if (live.battery_power_w or 0) > 25 else (
        "Urladdar" if (live.battery_power_w or 0) < -25 else "Vilar"
    )

    ev_kw = (ev_power_w or 0) / 1000
    spa_kw = (spa_power_w or 0) / 1000

    return DisplayFlowSection(
        available=True,
        nodes=[
            DisplayFlowNode(key="solar", label_sv="SOL", power_kw=round(solar_kw, 2)),
            DisplayFlowNode(key="battery", label_sv="BATTERI", power_kw=round(battery_kw, 2), status_sv=battery_dir),
            DisplayFlowNode(key="grid", label_sv="NÄT", power_kw=round(grid_kw, 2), status_sv=grid_dir),
            DisplayFlowNode(key="house", label_sv="HUS", power_kw=round(house_kw, 2)),
            DisplayFlowNode(
                key="charger",
                label_sv="LADDBOX",
                power_kw=round(ev_kw, 2),
                status_sv="Väntar" if ev_kw < 0.025 else "Laddar",
            ),
            DisplayFlowNode(
                key="spa",
                label_sv="SPA",
                power_kw=round(spa_kw, 2),
                status_sv="Standby" if spa_kw < 0.025 else "Aktiv",
            ),
        ],
    )


class DisplayOverviewService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def build(self, slug: str) -> DisplayOverviewResponse | None:
        cached = _OVERVIEW_CACHE.get(slug)
        if cached is not None and time.monotonic() - cached[0] <= _OVERVIEW_TTL_SECONDS:
            return cached[1]

        site = await SiteRepository(self._session).get_by_slug(slug)
        if site is None:
            return None

        reading_repo = EnergyReadingRepository(self._session, is_sqlite=self._settings.is_sqlite)
        latest = await reading_repo.get_latest_for_site(site.id)
        energy_snapshot = await EnergyStateService(self._session, self._settings).build_snapshot(site)

        freshness = DisplayFreshnessSection(connection_state="CONNECTED")
        if latest is not None:
            recorded_at = latest.recorded_at
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.replace(tzinfo=UTC)
            age = int((datetime.now(UTC) - recorded_at.astimezone(UTC)).total_seconds())
            freshness = DisplayFreshnessSection(
                updated_at=recorded_at,
                data_age_seconds=max(0, age),
                stale=age > STALE_SECONDS,
                connection_state="STALE" if age > STALE_SECONDS else "CONNECTED",
            )

        today = await _compute_today(self._session, site, self._settings)
        price = await _compute_price(self._session, site, self._settings)
        ev = await _compute_ev(self._session, site, self._settings)

        spa_row = await ConsumerRepository(self._session).get_spa_by_site_slug(slug)
        spa_enabled = bool(spa_row and spa_row[1].integration_enabled)
        from energy_core.db.vehicle_repo import VehicleProviderRepository

        vehicle_row = await VehicleProviderRepository(self._session).get_for_site(site.id)
        vehicle_enabled = bool(vehicle_row and vehicle_row.enabled)

        live_w = {
            "solar_production_w": latest.solar_production_w if latest else None,
            "consumption_w": latest.consumption_w if latest else None,
            "grid_import_w": latest.grid_import_w if latest else None,
            "grid_export_w": latest.grid_export_w if latest else None,
            "battery_soc_pct": latest.battery_soc_pct if latest else None,
            "battery_power_w": latest.battery_power_w if latest else None,
        }
        if ev.power_w is not None:
            live_w["ev_power_w"] = ev.power_w

        grid_export_kw = (live_w["grid_export_w"] or 0) / 1000
        grid_import_kw = (live_w["grid_import_w"] or 0) / 1000
        grid_net = grid_export_kw if grid_export_kw >= 0.025 else -grid_import_kw
        grid_dir = _grid_direction(grid_export_kw, grid_import_kw)
        grid_dir_sv = _GRID_DIRECTION_SV[grid_dir]

        soc = live_w["battery_soc_pct"]
        capacity = _DEFAULT_BATTERY_CAPACITY_KWH
        stored = round(capacity * (soc or 0) / 100, 1) if soc is not None else None

        solar_kw = (live_w["solar_production_w"] or 0) / 1000
        house_kw = (live_w["consumption_w"] or 0) / 1000
        surplus = max(0.0, solar_kw - house_kw)

        sparklines = await _sparklines_for_today(self._session, site, self._settings)
        weather = await _weather_section(self._session, site, self._settings)
        spa = await _spa_section(self._session, slug, spa_enabled)
        vehicle = await _vehicle_section(self._session, site.id, vehicle_enabled, ev)
        charger = await _charger_section(self._session, site, self._settings, ev, price.tier)
        economy = await _economy_section(self._session, site, self._settings)
        highlights = await _highlights_section(
            self._session,
            site,
            self._settings,
            today.produced_kwh,
            today.exported_kwh,
            energy_snapshot,
        )

        class _Live:
            solar_production_w = live_w["solar_production_w"]
            consumption_w = live_w["consumption_w"]
            grid_import_w = live_w["grid_import_w"]
            grid_export_w = live_w["grid_export_w"]
            battery_power_w = live_w["battery_power_w"]

        flow = _flow_section(_Live(), ev.power_w, spa.power_w)

        healthy = not freshness.stale and latest is not None
        if ev.available and ev.display_status_sv and "fel" in ev.display_status_sv.lower():
            healthy = False
        system_status = DisplaySystemStatusSection(
            healthy=healthy,
            status_sv="Allt normalt" if healthy else "Avvikelse",
            detail_sv="Alla system fungerar som de ska." if healthy else "En eller flera integrationer behöver uppmärksamhet.",
        )

        response = DisplayOverviewResponse(
            generated_at=datetime.now(UTC),
            site=DisplaySiteSection(slug=site.slug, name=site.name, timezone=site.timezone),
            freshness=freshness,
            live=DisplayLiveMetrics(
                solar_power_kw=round(solar_kw, 2) if latest else None,
                house_power_kw=round(house_kw, 2) if latest else None,
                grid_net_power_kw=round(abs(grid_net), 2) if latest else None,
                grid_direction=grid_dir,
                grid_direction_sv=grid_dir_sv,
                battery_soc_pct=soc,
                battery_power_kw=round((live_w["battery_power_w"] or 0) / 1000, 2) if latest else None,
                battery_state_sv=energy_snapshot.battery_state_text_sv,
                battery_stored_kwh=stored,
                battery_capacity_kwh=capacity if soc is not None else None,
                solar_surplus_kw=round(surplus, 2) if latest else None,
                produced_today_kwh=today.produced_kwh,
                consumed_today_kwh=today.consumed_kwh,
                imported_today_kwh=today.imported_kwh,
                exported_today_kwh=today.exported_kwh,
                self_consumption_pct=energy_snapshot.self_consumption_percent,
                self_sufficiency_pct=energy_snapshot.self_sufficiency_percent,
                battery_soh_pct=None,
            ),
            sparklines=sparklines,
            weather=weather,
            price=DisplayPriceSection(
                available=price.unavailable_reason is None,
                unavailable_reason=price.unavailable_reason,
                tier=price.tier,
                tier_label_sv=_tier_label(price.tier),
                current_ore_kwh=_ore_from_eur(price.current_eur_kwh),
            ),
            flow=flow,
            vehicle=vehicle,
            charger=charger,
            spa=spa,
            economy=economy,
            highlights=highlights,
            system_status=system_status,
        )
        _OVERVIEW_CACHE[slug] = (time.monotonic(), response)
        return response
