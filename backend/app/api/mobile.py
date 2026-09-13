"""Mobile PWA summary API."""

from __future__ import annotations

from typing import Annotated

from app.api.multi_site import MULTISITE_CACHE_TTL, MultiSiteOverviewRequest, _resolve_authorized_sites
from app.deps import get_app_settings, get_db_session
from app.user_auth import require_permission
from energy_core.auth.principal import Principal
from energy_core.cache.service import get_cache_service
from energy_core.config import Settings
from energy_core.mobile.summary import build_mobile_summary
from energy_core.multi_site.service import MultiSiteAggregationService, multisite_cache_key
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.post("/summary")
async def mobile_summary(
    body: MultiSiteOverviewRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal: Annotated[Principal, Depends(require_permission("dashboard.read"))],
) -> dict:
    sites = await _resolve_authorized_sites(session, principal, settings, body.site_slugs)
    cache_key = f"{multisite_cache_key([s.slug for s in sites])}:mobile"
    cache = get_cache_service(settings)

    async def build():
        service = MultiSiteAggregationService(session, settings)
        overview = await service.build_overview(sites)
        return build_mobile_summary(overview, principal)

    return await cache.get_or_set(cache_key, build, ttl_seconds=MULTISITE_CACHE_TTL)
