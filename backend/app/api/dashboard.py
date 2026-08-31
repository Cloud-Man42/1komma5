"""Aggregated dashboard endpoint for site overview."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.api.energy_balance_helpers import snapshot_to_response
from app.deps import get_app_settings, get_db_session
from app.schemas import (
    DashboardAlert,
    DashboardEvSection,
    DashboardFreshnessSection,
    DashboardLiveSection,
    DashboardOptimizationSection,
    DashboardPriceSection,
    DashboardResponse,
    DashboardSiteSection,
    DashboardSolarSection,
    DashboardTodaySection,
    DashboardVehicleSection,
)
from energy_core.charging.engine import bridge_status_from_charger
from energy_core.energy.integration import integrate_site_energy
from energy_core.charging.reasoning import build_energy_reasoning
from energy_core.charging.solar_plan import load_solar_charging_plan_for_charger
from energy_core.config import Settings
from energy_core.db.energy_balance_repo import EnergyBalanceRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EnergyReadingModel
from energy_core.db.repositories import EnergyReadingRepository, MarketPriceRepository, SiteRepository
from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.db.solar_forecast_repo import SolarForecastRepository, SolarSiteConfigRepository
from energy_core.energy.state import EnergyState
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["dashboard"])

STALE_SECONDS = 480
_CACHE: dict[tuple[str, str], tuple[float, Any]] = {}
_TTL = {
    "today": 60.0,
    "price": 300.0,
    "solar": 900.0,
    "optimization": 900.0,
}


def _cache_get(site_slug: str, section: str, ttl: float) -> Any | None:
    if ttl <= 0:
        return None
    key = (site_slug, section)
    entry = _CACHE.get(key)
    if entry is None:
        return None
    cached_at, value = entry
    if time.monotonic() - cached_at > ttl:
        return None
    return value


def _cache_set(site_slug: str, section: str, value: Any) -> None:
    _CACHE[(site_slug, section)] = (time.monotonic(), value)


def _battery_direction(power_w: float | None) -> str | None:
    if power_w is None:
        return None
    if power_w > 25:
        return "charging"
    if power_w < -25:
        return "discharging"
    return "idle"


async def _compute_today(session: AsyncSession, site, settings: Settings) -> DashboardTodaySection:
    cached = _cache_get(site.slug, "today", _TTL["today"])
    if cached is not None:
        return cached

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
            EnergyReadingModel.battery_power_w,
        )
        .where(
            EnergyReadingModel.site_id == site.id,
            EnergyReadingModel.recorded_at >= start_utc,
            EnergyReadingModel.recorded_at <= now_utc,
        )
        .order_by(EnergyReadingModel.recorded_at)
    )
    readings = (await session.execute(stmt)).all()
    if len(readings) < 2:
        section = DashboardTodaySection(unavailable_reason="Otillräcklig mätdata idag")
        _cache_set(site.slug, "today", section)
        return section

    totals = integrate_site_energy(readings)
    produced = totals.solar_kwh
    consumed = totals.consumption_kwh
    imported = totals.import_kwh
    exported = totals.export_kwh

    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    stats = await reading_repo.list_financial_stats(
        site_id=site.id,
        period="day",
        timezone=site.timezone,
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        from_time=start_utc,
        to_time=now_utc + timedelta(seconds=1),
        sell_config=sell_price_config_from_site(site),
    )
    today_key = now_local.strftime("%Y-%m-%d")
    stat = next((row for row in stats if row.period_start == today_key), None)
    energy_cost = None
    savings = None
    if stat is not None:
        energy_cost = round(stat.grid_import_cost_sek - stat.export_revenue_sek, 2)
        savings = round(stat.solar_savings_sek + stat.battery_savings_sek, 2)

    section = DashboardTodaySection(
        produced_kwh=round(produced, 1),
        consumed_kwh=round(consumed, 1),
        imported_kwh=round(imported, 1),
        exported_kwh=round(exported, 1),
        energy_cost_sek=energy_cost,
        savings_sek=savings,
    )
    _cache_set(site.slug, "today", section)
    return section


async def _price_from_db(session: AsyncSession, site, settings: Settings) -> tuple[float | None, tuple[tuple[datetime, float], ...], DashboardPriceSection]:
    price_repo = MarketPriceRepository(session, is_sqlite=settings.is_sqlite)
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    prices = await price_repo.list_between(
        site.id,
        from_time=now - timedelta(hours=1),
        to_time=now + timedelta(hours=23),
    )
    if not prices:
        section = DashboardPriceSection(unavailable_reason="Elpris otillgängligt")
        return None, (), section

    forecast = tuple(
        (row.recorded_at, row.all_in_price_eur_kwh or row.spot_price_eur_kwh) for row in prices
    )
    current_row = next((row for row in prices if row.recorded_at <= now), prices[0])
    current = current_row.all_in_price_eur_kwh or current_row.spot_price_eur_kwh
    all_in_values = [row.all_in_price_eur_kwh or row.spot_price_eur_kwh for row in prices]
    avg = sum(all_in_values) / len(all_in_values)
    tier = "normal"
    if current <= avg * 0.85:
        tier = "green"
    elif current >= avg * 1.15:
        tier = "red"
    section = DashboardPriceSection(
        current_eur_kwh=current,
        lowest_eur_kwh=min(all_in_values),
        highest_eur_kwh=max(all_in_values),
        tier=tier,
    )
    return current, forecast, section


async def _compute_price(session: AsyncSession, site, settings: Settings) -> DashboardPriceSection:
    cached = _cache_get(site.slug, "price", _TTL["price"])
    if cached is not None:
        return cached

    _, _, section = await _price_from_db(session, site, settings)
    _cache_set(site.slug, "price", section)
    return section


async def _compute_solar(session: AsyncSession, site) -> DashboardSolarSection:
    cached = _cache_get(site.slug, "solar", _TTL["solar"])
    if cached is not None:
        return cached

    config_repo = SolarSiteConfigRepository(session)
    config = await config_repo.get(site.id, timezone=site.timezone)
    if config is None or not config.enabled:
        section = DashboardSolarSection(unavailable_reason="Solprognos är inte aktiverad")
        _cache_set(site.slug, "solar", section)
        return section

    from energy_core.solar_forecast.day_metrics import compute_solar_day_metrics

    forecast_repo = SolarForecastRepository(session)
    forecast = await forecast_repo.get_latest(site.id)
    if forecast is None:
        section = DashboardSolarSection(unavailable_reason="Ingen cachad solprognos")
        _cache_set(site.slug, "solar", section)
        return section

    day_metrics = compute_solar_day_metrics(forecast, timezone=site.timezone)
    confidence_pct = round(float(forecast.confidence or 0) * 100, 1) if forecast.confidence is not None else None
    section = DashboardSolarSection(
        expected_today_kwh=round(float(day_metrics.expected_today_kwh or 0), 1),
        remaining_kwh=round(float(day_metrics.remaining_today_kwh or 0), 1),
        peak_power_w=float(day_metrics.peak_power_w or 0) or None,
        peak_at=day_metrics.peak_time,
        confidence_pct=confidence_pct,
        inverter_max_power_kw=float(config.inverter_max_power_kw or 0) or None,
    )
    _cache_set(site.slug, "solar", section)
    return section


async def _compute_ev(session: AsyncSession, site, settings: Settings) -> DashboardEvSection:
    repo = EvChargerRepository(session)
    chargers = await repo.list_for_site(site.id)
    if not chargers:
        return DashboardEvSection(available=False, unavailable_reason="Ingen laddbox konfigurerad")

    charger = next((item for item in chargers if item.bridge_enabled), chargers[0])
    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    latest = await balance_repo.get_latest(site_id=site.id, charger_id=charger.id)
    balance = snapshot_to_response(latest, charger_id=charger.id) if latest else None
    energy = None
    if balance and balance.status != "UNAVAILABLE":
        energy = EnergyState(
            timestamp=balance.recorded_at or datetime.now(UTC),
            grid_import_w=balance.sungrow_grid_import_w,
            home_consumption_w=balance.heartbeat_home_consumption_w,
            ev_actual_power_w=balance.heartbeat_observed_ev_power_w,
        )
    status_record = bridge_status_from_charger(charger, site=site, energy=energy)
    power_w = status_record.actual_power_w or (energy.ev_actual_power_w if energy else None) or charger.last_actual_power_w
    charging = (power_w or 0) >= 25

    return DashboardEvSection(
        available=True,
        charging=charging,
        charging_mode=status_record.charging_mode,
        display_status_sv=status_record.display_status_sv,
        power_w=power_w,
    )


async def _compute_vehicle(session: AsyncSession, site) -> DashboardVehicleSection:
    from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRepository
    from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
    from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS

    provider = await VehicleProviderRepository(session).get_for_site(site.id)
    if provider is None or not provider.enabled:
        return DashboardVehicleSection(unavailable_reason="Mercedes-integration är avstängd")

    vehicles = await VehicleRepository(session).list_for_site(site.id)
    if not vehicles:
        return DashboardVehicleSection(unavailable_reason="Inget fordon registrerat")

    vehicle = vehicles[0]
    latest = await VehicleRepository(session).get_latest_state(vehicle.id)
    active = await VehicleChargeSessionRepository(session).get_active_for_vehicle(vehicle.id)

    is_charging = bool(latest and latest.is_charging)
    is_plugged = bool(latest and latest.is_plugged_in)
    stale = False
    freshness = "LIVE"
    if latest and latest.last_vehicle_update:
        ts = latest.last_vehicle_update
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - ts).total_seconds()
        stale = age > STALE_TELEMETRY_SECONDS
        freshness = "INAKTUELL" if stale else "LIVE"

    mode = "charging" if is_charging else "parked"
    session_energy = None
    if active is not None:
        session_energy = active.halo_energy_kwh or active.estimated_energy_kwh

    return DashboardVehicleSection(
        available=True,
        display_name=vehicle.display_name,
        mode=mode,
        state_of_charge_percent=latest.state_of_charge_percent if latest and not stale else None,
        electric_range_km=latest.electric_range_km if latest and not stale else None,
        is_plugged_in=is_plugged if latest and not stale else None,
        is_charging=is_charging if latest and not stale else None,
        charging_power_kw=latest.charging_power_kw if latest and not stale else None,
        location_name=active.location_name if active else None,
        charging_type=active.charging_type if active else None,
        session_energy_kwh=session_energy,
        data_quality=active.vehicle_data_quality if active else (latest.data_quality if latest else None),
        freshness_label=freshness,
    )


async def _fetch_price_forecast(session: AsyncSession, site, settings: Settings) -> tuple[float | None, tuple[tuple[datetime, float], ...]]:
    current, forecast, _ = await _price_from_db(session, site, settings)
    return current, forecast


def _energy_for_optimization(
    balance,
    live: DashboardLiveSection | None,
    *,
    current_price: float | None,
    price_forecast: tuple[tuple[datetime, float], ...],
) -> EnergyState | None:
    if balance is None and live is None and current_price is None:
        return None
    timestamp = balance.recorded_at if balance is not None else datetime.now(UTC)
    return EnergyState(
        timestamp=timestamp or datetime.now(UTC),
        electricity_price_eur_kwh=current_price,
        price_forecast=price_forecast,
        pv_power_w=live.solar_production_w if live else None,
        grid_import_w=(
            balance.sungrow_grid_import_w
            if balance is not None and balance.status != "UNAVAILABLE"
            else (live.grid_import_w if live else None)
        ),
        grid_export_w=live.grid_export_w if live else None,
        home_consumption_w=(
            balance.heartbeat_home_consumption_w
            if balance is not None and balance.status != "UNAVAILABLE"
            else (live.consumption_w if live else None)
        ),
        ev_actual_power_w=(
            balance.heartbeat_observed_ev_power_w
            if balance is not None and balance.status != "UNAVAILABLE"
            else (live.ev_power_w if live else None)
        ),
        battery_soc=live.battery_soc_pct if live else None,
    )


async def _compute_optimization(
    session: AsyncSession,
    site,
    settings: Settings,
    live: DashboardLiveSection | None,
) -> DashboardOptimizationSection:
    cached = _cache_get(site.slug, "optimization", _TTL["optimization"])
    if cached is not None:
        return cached

    repo = EvChargerRepository(session)
    chargers = await repo.list_for_site(site.id)
    bridge_charger = next((item for item in chargers if item.bridge_enabled), None)
    if bridge_charger is None:
        section = DashboardOptimizationSection(
            strategy_sv="Ingen SmartLaddning aktiv",
            explanation_sv=(
                "EMIC styr inte laddboxen automatiskt. Aktivera bridge under Konfiguration "
                "för smart laddning med solel, elpris och EV-behov."
            ),
            reasoning_steps=[
                "EMIC-styrning är avstängd — laddboxen styrs inte automatiskt.",
                "Aktivera bridge under Konfiguration för att styra laddboxen.",
            ],
        )
        _cache_set(site.slug, "optimization", section)
        return section

    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    latest = await balance_repo.get_latest(site_id=site.id, charger_id=bridge_charger.id)
    balance = snapshot_to_response(latest, charger_id=bridge_charger.id) if latest else None
    current_price, price_forecast = await _fetch_price_forecast(session, site, settings)
    energy = _energy_for_optimization(
        balance,
        live,
        current_price=current_price,
        price_forecast=price_forecast,
    )
    status_record = bridge_status_from_charger(bridge_charger, site=site, energy=energy)
    plan = await load_solar_charging_plan_for_charger(
        session,
        site,
        bridge_charger,
        price_forecast=price_forecast,
        current_price=current_price,
    )
    reasoning = build_energy_reasoning(
        charger=bridge_charger,
        site=site,
        energy=energy,
        solar_plan=plan,
    )

    strategy = status_record.display_status_sv or "Smart laddning aktiv"
    explanation = plan.explanation_sv if plan is not None else None
    steps = list(reasoning.reasoning_steps)
    if explanation is None and steps:
        explanation = " ".join(steps[:2])

    section = DashboardOptimizationSection(
        strategy_sv=strategy,
        explanation_sv=explanation,
        reasoning_steps=steps,
        solar_first=plan.solar_first if plan is not None else None,
        battery_soc_pct=live.battery_soc_pct if live else None,
    )
    _cache_set(site.slug, "optimization", section)
    return section


def _build_alerts(
    freshness: DashboardFreshnessSection,
    ev: DashboardEvSection | None,
    live: DashboardLiveSection | None,
) -> list[DashboardAlert]:
    alerts: list[DashboardAlert] = []
    if freshness.stale:
        alerts.append(
            DashboardAlert(
                severity="warning",
                message_sv=f"Mätdata har inte uppdaterats på {freshness.data_age_seconds or 0} sek.",
            )
        )
    if live is None:
        alerts.append(
            DashboardAlert(
                severity="warning",
                message_sv="Ingen live-mätdata tillgänglig.",
            )
        )
    if ev and ev.available and ev.display_status_sv and "fel" in ev.display_status_sv.lower():
        alerts.append(DashboardAlert(severity="danger", message_sv=ev.display_status_sv))
    return alerts


@router.get("/sites/{slug}/dashboard", response_model=DashboardResponse)
async def get_site_dashboard(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> DashboardResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    latest = await reading_repo.get_latest_for_site(site.id)

    freshness = DashboardFreshnessSection()
    live: DashboardLiveSection | None = None
    if latest is not None:
        recorded_at = latest.recorded_at
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        age = int((datetime.now(UTC) - recorded_at.astimezone(UTC)).total_seconds())
        freshness = DashboardFreshnessSection(
            updated_at=recorded_at,
            data_age_seconds=max(0, age),
            stale=age > STALE_SECONDS,
        )
        live = DashboardLiveSection(
            solar_production_w=latest.solar_production_w,
            consumption_w=latest.consumption_w,
            grid_import_w=latest.grid_import_w,
            grid_export_w=latest.grid_export_w,
            battery_soc_pct=latest.battery_soc_pct,
            battery_power_w=latest.battery_power_w,
            battery_direction=_battery_direction(latest.battery_power_w),
            ev_power_w=None,
        )

    ev_section = await _compute_ev(session, site, settings)
    vehicle_section = await _compute_vehicle(session, site)
    if live is not None and ev_section.power_w is not None:
        live = live.model_copy(update={"ev_power_w": ev_section.power_w})

    today_section = await _compute_today(session, site, settings)
    solar_section = await _compute_solar(session, site)
    price_section = await _compute_price(session, site, settings)
    optimization_section = await _compute_optimization(session, site, settings, live)

    from energy_core.db.consumer_repo import ConsumerRepository

    spa_row = await ConsumerRepository(session).get_spa_by_site_slug(slug)
    spa_enabled = bool(spa_row and spa_row[1].integration_enabled)

    from energy_core.db.vehicle_repo import VehicleProviderRepository

    vehicle_row = await VehicleProviderRepository(session).get_for_site(site.id)
    vehicle_enabled = bool(vehicle_row and vehicle_row.enabled)

    alerts = _build_alerts(freshness, ev_section, live)

    return DashboardResponse(
        site=DashboardSiteSection(slug=site.slug, name=site.name, timezone=site.timezone),
        freshness=freshness,
        live=live,
        today=today_section,
        ev=ev_section,
        vehicle=vehicle_section,
        solar=solar_section,
        price=price_section,
        optimization=optimization_section,
        alerts=alerts,
        spa_integration_enabled=spa_enabled,
        vehicle_integration_enabled=vehicle_enabled,
    )
