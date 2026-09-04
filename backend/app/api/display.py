"""Raspberry Pi display overview API."""

from __future__ import annotations

import asyncio
import re

from app.display_auth import (
    DISPLAY_COOKIE_MAX_AGE_SECONDS,
    DISPLAY_COOKIE_NAME,
    authenticate_display_token,
    require_display_device,
)
from app.display_service import DisplayOverviewService
from app.deps import get_app_settings, get_db_session
from app.schemas_display import DisplayOverviewResponse
from energy_core.cache.snapshot_pubsub import listen_snapshot_events, snapshot_pubsub_available
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/display", tags=["display"])

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@router.get("/overview/{slug}", response_model=DisplayOverviewResponse)
async def get_display_overview(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _device=Depends(require_display_device),
) -> DisplayOverviewResponse:
    overview = await DisplayOverviewService(session, settings).build(slug)
    if overview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return overview


async def _display_overview_sse_generator(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    slug: str,
    service: DisplayOverviewService,
):
    last_generated_at: str | None = None

    def format_overview(overview: DisplayOverviewResponse | None) -> str | None:
        nonlocal last_generated_at
        if overview is None:
            return None
        if overview.generated_at != last_generated_at:
            last_generated_at = overview.generated_at
            return f"data: {overview.model_dump_json()}\n\n"
        return None

    initial = await service.build(slug)
    if initial is None:
        return
    if chunk := format_overview(initial):
        yield chunk

    site = await SiteRepository(session).get_by_slug(slug)
    if site is not None and await snapshot_pubsub_available(settings):
        async for _event in listen_snapshot_events(settings, site.id):
            if await request.is_disconnected():
                return
            overview = await service.build(slug)
            if overview is None:
                break
            if chunk := format_overview(overview):
                yield chunk
        if await request.is_disconnected():
            return

    while True:
        if await request.is_disconnected():
            break
        overview = await service.build(slug)
        if overview is None:
            break
        if chunk := format_overview(overview):
            yield chunk
        await asyncio.sleep(1)


@router.get("/overview/{slug}/stream")
async def stream_display_overview(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _device=Depends(require_display_device),
) -> StreamingResponse:
    service = DisplayOverviewService(session, settings)

    async def event_generator():
        async for chunk in _display_overview_sse_generator(
            request,
            session,
            settings,
            slug,
            service,
        ):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/enroll", include_in_schema=False)
async def enroll_display_browser(
    request: Request,
    token: str = Query(min_length=1, max_length=256),
    slug: str | None = Query(default=None, max_length=64),
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """Trade a one-time link for a long-lived HttpOnly cookie.

    A browser without the Pi's token-injecting proxy opens this link once. The
    token is validated before the cookie is set, and the redirect drops it from
    the address bar and browser history.
    """
    token = token.strip()
    device = await authenticate_display_token(token, session)

    target_slug = (slug or device.record.default_site_slug or "").strip().lower()
    # Guards the redirect target, which would otherwise be attacker-controlled.
    if not _SLUG_PATTERN.match(target_slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A site slug is required when the device has no default site",
        )

    response = RedirectResponse(
        url=f"/display/{target_slug}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        DISPLAY_COOKIE_NAME,
        token,
        max_age=DISPLAY_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        # The LAN deployment serves plain HTTP, where a Secure cookie is dropped.
        secure=request.url.scheme == "https",
        path="/",
    )
    return response
