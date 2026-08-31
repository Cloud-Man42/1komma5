"""Raspberry Pi display overview API."""

from __future__ import annotations

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
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
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
