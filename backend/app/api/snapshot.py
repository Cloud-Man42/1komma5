"""Site snapshot read endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.deps import get_app_settings, get_db_session
from energy_core.cache.service import get_cache_service, site_snapshot_cache_key
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from energy_core.db.snapshot_repo import SiteLiveSnapshotRepository
from energy_core.performance.context import get_performance_context
from energy_core.snapshots.writer import SiteSnapshotBuilder
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["snapshot"])

SNAPSHOT_CACHE_TTL = 5.0


async def _load_snapshot(session: AsyncSession, site, settings: Settings) -> dict[str, Any]:
    cache = get_cache_service()
    cache_key = site_snapshot_cache_key(site.id)

    async def factory() -> dict[str, Any]:
        repo = SiteLiveSnapshotRepository(session, is_sqlite=settings.is_sqlite)
        stored = await repo.get_for_site(site.id)
        if stored is not None:
            return stored
        return await SiteSnapshotBuilder(settings).build(session, site)

    ctx = get_performance_context()
    cached = await cache.get(cache_key)
    if cached is not None:
        if ctx is not None:
            ctx.cache_hit = True
        return cached

    payload = await cache.get_or_set(cache_key, factory, ttl_seconds=SNAPSHOT_CACHE_TTL)
    return payload


def _summary_from_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    live = payload.get("live") or {}
    today = payload.get("today") or {}
    return {
        "generated_at": payload.get("generated_at"),
        "age_seconds": payload.get("age_seconds"),
        "freshness": payload.get("freshness"),
        "solar_production_w": live.get("solar_production_w"),
        "consumption_w": live.get("consumption_w"),
        "produced_kwh": today.get("produced_kwh"),
        "consumed_kwh": today.get("consumed_kwh"),
    }


@router.get("/sites/{slug}/snapshot")
async def get_site_snapshot(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    ctx = get_performance_context()
    if ctx is not None:
        ctx.site_id = site.id
    return await _load_snapshot(session, site, settings)


@router.get("/sites/{slug}/snapshot/summary")
async def get_site_snapshot_summary(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    payload = await _load_snapshot(session, site, settings)
    return _summary_from_snapshot(payload)


@router.get("/sites/{slug}/live-stream")
async def site_live_stream(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            payload = await _load_snapshot(session, site, settings)
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/kiosk/{slug}/snapshot")
async def kiosk_snapshot(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    payload = await get_site_snapshot(slug, session, settings)
    return _summary_from_snapshot(payload)


@router.get("/kiosk/{slug}/stream")
async def kiosk_stream(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    return await site_live_stream(slug, request, session, settings)
