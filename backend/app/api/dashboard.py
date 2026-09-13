"""Aggregated dashboard endpoint for site overview."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.dashboard_compute import (
    STALE_SECONDS,
    _CACHE,
    _battery_direction,
    _build_alerts,
    _compute_ev,
    _compute_optimization,
    _compute_price,
    _compute_solar,
    _compute_today,
    _compute_vehicle,
)
from app.deps import get_app_settings, get_db_session
from app.site_access import require_site_with_permission
from app.user_auth import require_authenticated
from energy_core.auth.principal import Principal

from app.schemas.dashboard import (
    DashboardEvSection,
    DashboardFreshnessSection,
    DashboardLiveSection,
    DashboardResponse,
    DashboardSiteSection,
)
from energy_core.cache.service import get_cache_service, site_dashboard_cache_key
from energy_core.config import Settings
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.performance.context import get_performance_context
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["dashboard"])

__all__ = ["STALE_SECONDS", "_CACHE", "router"]


@router.get("/sites/{slug}/dashboard", response_model=DashboardResponse)
async def get_site_dashboard(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    principal: Principal = Depends(require_authenticated),
) -> DashboardResponse:
    site = await require_site_with_permission(session, principal, settings, slug, "dashboard.read")

    cache = get_cache_service(settings)
    cache_key = site_dashboard_cache_key(site.id)
    ttl_seconds = settings.dashboard_redis_cache_ttl_seconds

    async def factory() -> dict[str, Any]:
        response = await _build_dashboard_response(session, site, settings)
        return response.model_dump(mode="json")

    ctx = get_performance_context()
    cached = await cache.get(cache_key)
    if cached is not None:
        if ctx is not None:
            ctx.cache_hit = True
        refreshed = await _refresh_live_sections(session, site, settings, cached)
        return DashboardResponse.model_validate(refreshed)

    payload = await cache.get_or_set(cache_key, factory, ttl_seconds=ttl_seconds)
    return DashboardResponse.model_validate(payload)


async def _refresh_live_sections(
    session: AsyncSession,
    site,
    settings: Settings,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Recompute freshness/live/alerts on cache hits so stale warnings recover quickly."""
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    latest = await reading_repo.get_latest_for_site(site.id)
    freshness, live = _freshness_and_live_from_reading(latest)

    ev_section = DashboardEvSection.model_validate(payload.get("ev") or {"available": False})
    if live is not None and ev_section.power_w is not None:
        live = live.model_copy(update={"ev_power_w": ev_section.power_w})

    alerts = _build_alerts(
        freshness,
        ev_section,
        live,
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a or 2.0,
    )
    updated = dict(payload)
    updated["freshness"] = freshness.model_dump(mode="json")
    updated["live"] = live.model_dump(mode="json") if live is not None else None
    updated["alerts"] = [alert.model_dump(mode="json") for alert in alerts]
    return updated


def _freshness_and_live_from_reading(
    latest,
) -> tuple[DashboardFreshnessSection, DashboardLiveSection | None]:
    if latest is None:
        return DashboardFreshnessSection(), None

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
    return freshness, live


async def _build_dashboard_response(
    session: AsyncSession,
    site,
    settings: Settings,
) -> DashboardResponse:
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    latest = await reading_repo.get_latest_for_site(site.id)
    freshness, live = _freshness_and_live_from_reading(latest)

    ev_section, vehicle_section, today_section, solar_section, price_section = await asyncio.gather(
        _compute_ev(session, site, settings),
        _compute_vehicle(session, site),
        _compute_today(session, site, settings),
        _compute_solar(session, site),
        _compute_price(session, site, settings),
    )
    if live is not None and ev_section.power_w is not None:
        live = live.model_copy(update={"ev_power_w": ev_section.power_w})

    optimization_section = await _compute_optimization(session, site, settings, live)

    from energy_core.db.consumer_repo import ConsumerRepository
    from energy_core.db.vehicle_repo import VehicleProviderRepository

    spa_row, vehicle_row = await asyncio.gather(
        ConsumerRepository(session).get_spa_by_site_slug(site.slug),
        VehicleProviderRepository(session).get_for_site(site.id),
    )
    spa_enabled = bool(spa_row and spa_row[1].integration_enabled)
    vehicle_enabled = bool(vehicle_row and vehicle_row.enabled)

    alerts = _build_alerts(
        freshness,
        ev_section,
        live,
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a or 2.0,
    )

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
