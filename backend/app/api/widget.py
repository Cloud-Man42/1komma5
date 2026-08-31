"""Read-only Apple Widget API.

Power sign convention (all values in kW unless noted):
- solar.powerKw > 0: production
- house.powerKw > 0: consumption
- battery.powerKw > 0: battery charging; < 0: discharging
- grid.powerKw > 0: import from grid; < 0: export to grid
- ev.powerKw > 0: EV charging
"""

from __future__ import annotations

import time

from app.deps import get_app_settings, get_db_session
from app.schemas_widget import (
    WidgetMeResponse,
    WidgetSiteListItem,
    WidgetSitesResponse,
    WidgetStatusResponse,
    WidgetSummaryResponse,
    WidgetSummaryTotals,
    snapshot_to_widget_status,
)
from app.widget_auth import AuthenticatedWidgetDevice, log_widget_request, require_widget_device
from app.widget_service import WidgetSnapshotService
from energy_core.config import Settings
from energy_core.db.apple_device_repo import AppleDeviceRepository
from energy_core.db.repositories import SiteRepository
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/widget", tags=["Apple Widget API"])


async def _resolve_site(
    session: AsyncSession,
    *,
    site_slug: str | None,
    default_site_slug: str | None,
):
    site_repo = SiteRepository(session)
    if site_slug:
        site = await site_repo.get_by_slug(site_slug)
        if site is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
        return site
    if default_site_slug:
        site = await site_repo.get_by_slug(default_site_slug)
        if site is not None:
            return site
    sites = await site_repo.list_all()
    if not sites:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sites configured")
    return sites[0]


@router.get(
    "/sites",
    response_model=WidgetSitesResponse,
    summary="List widget-visible sites",
)
async def list_widget_sites(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    device: AuthenticatedWidgetDevice = Depends(require_widget_device),
) -> WidgetSitesResponse:
    started = time.perf_counter()
    service = WidgetSnapshotService(session, settings)
    site_repo = SiteRepository(session)
    sites = await site_repo.list_all()
    items: list[WidgetSiteListItem] = []
    for site in sites:
        snapshot = await service.get_snapshot(site)
        items.append(
            WidgetSiteListItem(
                id=site.slug,
                name=site.name,
                timezone=site.timezone,
                system_status=snapshot.system_status.value,
            )
        )
    response = WidgetSitesResponse(sites=items)
    log_widget_request(
        device_id=device.record.id,
        site_id=None,
        endpoint="/api/v1/widget/sites",
        status_code=200,
        duration_ms=(time.perf_counter() - started) * 1000,
        snapshot_age=None,
    )
    return response


@router.get(
    "/status",
    response_model=WidgetStatusResponse,
    summary="Widget status for default site",
)
async def get_widget_status_default(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    device: AuthenticatedWidgetDevice = Depends(require_widget_device),
) -> WidgetStatusResponse:
    started = time.perf_counter()
    site = await _resolve_site(
        session,
        site_slug=None,
        default_site_slug=device.record.default_site_slug,
    )
    service = WidgetSnapshotService(session, settings)
    snapshot = await service.get_snapshot(site)
    response = snapshot_to_widget_status(snapshot)
    await AppleDeviceRepository(session).touch_last_seen(device.record.id)
    await session.commit()
    log_widget_request(
        device_id=device.record.id,
        site_id=site.slug,
        endpoint="/api/v1/widget/status",
        status_code=200,
        duration_ms=(time.perf_counter() - started) * 1000,
        snapshot_age=snapshot.data_age_seconds,
    )
    return response


@router.get(
    "/status/{site_id}",
    response_model=WidgetStatusResponse,
    summary="Widget status for a specific site",
)
async def get_widget_status_for_site(
    site_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    device: AuthenticatedWidgetDevice = Depends(require_widget_device),
) -> WidgetStatusResponse:
    started = time.perf_counter()
    site = await _resolve_site(session, site_slug=site_id, default_site_slug=None)
    service = WidgetSnapshotService(session, settings)
    snapshot = await service.get_snapshot(site)
    response = snapshot_to_widget_status(snapshot)
    await AppleDeviceRepository(session).touch_last_seen(device.record.id)
    await session.commit()
    log_widget_request(
        device_id=device.record.id,
        site_id=site.slug,
        endpoint=f"/api/v1/widget/status/{site_id}",
        status_code=200,
        duration_ms=(time.perf_counter() - started) * 1000,
        snapshot_age=snapshot.data_age_seconds,
    )
    return response


@router.get(
    "/summary",
    response_model=WidgetSummaryResponse,
    summary="All sites with aggregate totals",
)
async def get_widget_summary(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    device: AuthenticatedWidgetDevice = Depends(require_widget_device),
) -> WidgetSummaryResponse:
    started = time.perf_counter()
    service = WidgetSnapshotService(session, settings)
    site_repo = SiteRepository(session)
    sites = await site_repo.list_all()
    statuses: list[WidgetStatusResponse] = []
    solar_total = 0.0
    house_total = 0.0
    saved_total = 0.0
    has_solar = has_house = has_saved = False
    max_age: int | None = None
    latest_updated = None
    any_stale = False

    snapshots = await service.get_snapshots(sites)
    for site, snapshot in zip(sites, snapshots):
        status_payload = snapshot_to_widget_status(snapshot)
        statuses.append(status_payload)
        if snapshot.solar_power_kw is not None:
            solar_total += snapshot.solar_power_kw
            has_solar = True
        if snapshot.house_power_kw is not None:
            house_total += snapshot.house_power_kw
            has_house = True
        if snapshot.saved_today_sek is not None:
            saved_total += snapshot.saved_today_sek
            has_saved = True
        if snapshot.data_age_seconds is not None:
            max_age = snapshot.data_age_seconds if max_age is None else max(max_age, snapshot.data_age_seconds)
        if snapshot.updated_at is not None and (latest_updated is None or snapshot.updated_at > latest_updated):
            latest_updated = snapshot.updated_at
        any_stale = any_stale or snapshot.is_stale

    response = WidgetSummaryResponse(
        sites=statuses,
        totals=WidgetSummaryTotals(
            solar_power_kw=round(solar_total, 3) if has_solar else None,
            house_power_kw=round(house_total, 3) if has_house else None,
            battery_stored_kwh=None,
            saved_today_sek=round(saved_total, 2) if has_saved else None,
        ),
        updated_at=latest_updated,
        data_age_seconds=max_age,
        is_stale=any_stale,
    )
    await AppleDeviceRepository(session).touch_last_seen(device.record.id)
    await session.commit()
    log_widget_request(
        device_id=device.record.id,
        site_id="all",
        endpoint="/api/v1/widget/summary",
        status_code=200,
        duration_ms=(time.perf_counter() - started) * 1000,
        snapshot_age=max_age,
    )
    return response


@router.get(
    "/me",
    response_model=WidgetMeResponse,
    summary="Validate device token and return profile",
)
async def get_widget_me(
    session: AsyncSession = Depends(get_db_session),
    device: AuthenticatedWidgetDevice = Depends(require_widget_device),
) -> WidgetMeResponse:
    await AppleDeviceRepository(session).touch_last_seen(device.record.id)
    await session.commit()
    scopes = [part.strip() for part in device.record.scopes.split(",") if part.strip()]
    return WidgetMeResponse(
        device_id=device.record.id,
        owner_label=device.record.owner_label,
        device_name=device.record.device_name,
        device_type=device.record.device_type,
        default_site_slug=device.record.default_site_slug,
        scopes=scopes,
        last_seen_at=device.record.last_seen_at,
    )
