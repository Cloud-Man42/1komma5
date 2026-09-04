"""ChargeFinder integration admin API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.schemas import (
    ChargeFinderDiagnosticsResponse,
    ChargeFinderRawLookupResponse,
    ChargeFinderStatusResponse,
    ChargeFinderTestLookupRequest,
    ChargeFinderTestLookupResponse,
)
from energy_core.config import get_settings
from energy_core.db.chargefinder_integration_status_repo import ChargeFinderIntegrationStatusRepository
from energy_core.db.vehicle_repo import VehicleRepository
from energy_core.integrations.charging_stations.chargefinder.provider import (
    ChargeFinderChargingStationProvider,
    ChargeFinderMode,
)
from energy_core.integrations.charging_stations.chargefinder_health import ChargeFinderIntegrationHealthService
from energy_core.integrations.charging_stations.chargefinder_metrics import get_chargefinder_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations/chargefinder", tags=["chargefinder"])


@router.get("/status", response_model=ChargeFinderStatusResponse)
async def chargefinder_status(
    session: AsyncSession = Depends(get_db_session),
) -> ChargeFinderStatusResponse:
    settings = get_settings()
    status_repo = ChargeFinderIntegrationStatusRepository(session)
    record = await status_repo.get_or_create()
    mode = ChargeFinderMode(str(settings.chargefinder_mode).upper())
    health = ChargeFinderIntegrationHealthService().evaluate(
        enabled=settings.chargefinder_enabled,
        mode=mode,
        status=record,
    )
    metrics = get_chargefinder_metrics().snapshot()
    return ChargeFinderStatusResponse(
        health_status=health.status.value,
        enabled=health.enabled,
        mode=health.mode,
        search_radius_m=settings.chargefinder_search_radius_m,
        cache_ttl_seconds=int(settings.chargefinder_cache_ttl_seconds),
        last_success_at=health.last_success_at,
        last_failure_at=health.last_failure_at,
        last_lookup_at=health.last_lookup_at,
        last_latency_ms=health.last_latency_ms,
        consecutive_failures=health.consecutive_failures,
        last_error=health.last_error,
        cache_hits=health.cache_hits,
        cache_misses=health.cache_misses,
        parser_failures=health.parser_failures,
        blocked_until=health.blocked_until,
        browser_status=health.browser_status,
        parsing_version=health.parsing_version,
        metrics=metrics,
    )


@router.get("/diagnostics", response_model=ChargeFinderDiagnosticsResponse)
async def chargefinder_diagnostics(
    session: AsyncSession = Depends(get_db_session),
) -> ChargeFinderDiagnosticsResponse:
    settings = get_settings()
    status_repo = ChargeFinderIntegrationStatusRepository(session)
    record = await status_repo.get_or_create()
    mode = ChargeFinderMode(str(settings.chargefinder_mode).upper())
    health = ChargeFinderIntegrationHealthService().evaluate(
        enabled=settings.chargefinder_enabled,
        mode=mode,
        status=record,
    )
    metrics = get_chargefinder_metrics().snapshot()
    return ChargeFinderDiagnosticsResponse(
        health_status=health.status.value,
        enabled=health.enabled,
        mode=health.mode,
        last_success_at=health.last_success_at,
        last_failure_at=health.last_failure_at,
        last_lookup_at=health.last_lookup_at,
        last_latency_ms=health.last_latency_ms,
        consecutive_failures=health.consecutive_failures,
        last_error=health.last_error,
        cache_hits=health.cache_hits,
        cache_misses=health.cache_misses,
        parser_failures=health.parser_failures,
        blocked_until=health.blocked_until,
        browser_status=health.browser_status,
        parsing_version=health.parsing_version,
        metrics=metrics,
    )


@router.post("/test-lookup", response_model=ChargeFinderTestLookupResponse)
async def chargefinder_test_lookup(
    payload: ChargeFinderTestLookupRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChargeFinderTestLookupResponse:
    settings = get_settings()
    if not settings.chargefinder_enabled or str(settings.chargefinder_mode).upper() == "DISABLED":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ChargeFinder is disabled")

    lat = payload.latitude
    lon = payload.longitude
    if payload.use_mercedes_position:
        if payload.site_slug is None:
            raise HTTPException(status_code=422, detail="site_slug required for Mercedes position")
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug(payload.site_slug)
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found")
        vehicles = await VehicleRepository(session).list_for_site(site.id)
        if not vehicles:
            raise HTTPException(status_code=404, detail="No vehicles found")
        latest = await VehicleRepository(session).get_latest_state(vehicles[0].id)
        if latest is None or latest.latitude is None or latest.longitude is None:
            raise HTTPException(status_code=404, detail="No Mercedes GPS position available")
        lat = latest.latitude
        lon = latest.longitude

    if lat is None or lon is None:
        raise HTTPException(status_code=422, detail="latitude and longitude required")

    radius = payload.radius_m or settings.chargefinder_search_radius_m
    allowed = {int(x.strip()) for x in settings.chargefinder_allowed_radius_options.split(",") if x.strip()}
    if radius not in allowed:
        raise HTTPException(status_code=422, detail=f"radius_m must be one of {sorted(allowed)}")

    provider = ChargeFinderChargingStationProvider.from_settings(settings)
    candidates = await provider.find_stations(latitude=lat, longitude=lon, radius_m=radius)
    return ChargeFinderTestLookupResponse(
        latitude=lat,
        longitude=lon,
        radius_m=radius,
        candidate_count=len(candidates),
        candidates=[
            {
                "provider_station_id": c.provider_station_id,
                "operator": c.operator,
                "station_name": c.station_name,
                "network_name": c.network_name,
                "distance_m": c.distance_m,
                "charging_type": c.charging_type,
                "max_power_kw": c.max_power_kw,
                "connector_type": c.connector_type,
                "price_model": c.price_model,
                "price_value_sek_kwh": c.price_value_sek_kwh,
                "external_url": c.external_url,
            }
            for c in candidates
        ],
    )


@router.get("/raw-lookup", response_model=ChargeFinderRawLookupResponse)
async def chargefinder_raw_lookup(
    latitude: float,
    longitude: float,
    radius_m: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ChargeFinderRawLookupResponse:
    settings = get_settings()
    if not settings.chargefinder_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ChargeFinder is disabled")
    radius = radius_m or settings.chargefinder_search_radius_m
    provider = ChargeFinderChargingStationProvider.from_settings(settings)
    candidates = await provider.find_stations(latitude=latitude, longitude=longitude, radius_m=radius)
    return ChargeFinderRawLookupResponse(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius,
        stations=[
            {
                "provider_station_id": c.provider_station_id,
                "operator": c.operator,
                "station_name": c.station_name,
                "network_name": c.network_name,
                "distance_m": c.distance_m,
                "charging_type": c.charging_type,
                "max_power_kw": c.max_power_kw,
                "connector_type": c.connector_type,
                "price_model": c.price_model,
                "price_value_sek_kwh": c.price_value_sek_kwh,
                "external_url": c.external_url,
                "raw_provider_data": c.raw_provider_data,
            }
            for c in candidates
        ],
    )
