"""Multi-site overview API."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.site_access import filter_sites_for_principal
from app.user_auth import require_permission
from energy_core.auth.permissions import PERMISSION_ALL
from energy_core.auth.principal import Principal
from energy_core.cache.service import get_cache_service
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from energy_core.multi_site.service import MultiSiteAggregationService, multisite_cache_key
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/multi-site", tags=["multi-site"])

MULTISITE_CACHE_TTL = 45.0


class MultiSiteOverviewRequest(BaseModel):
    site_slugs: list[str] = Field(min_length=1, max_length=32)


async def _resolve_authorized_sites(
    session: AsyncSession,
    principal: Principal,
    settings: Settings,
    slugs: list[str],
) -> list:
    unique_slugs = list(dict.fromkeys(s.strip() for s in slugs if s.strip()))
    if not unique_slugs:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No sites requested")

    repo = SiteRepository(session)
    sites = []
    for slug in unique_slugs:
        site = await repo.get_by_slug(slug)
        if site is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Site not found: {slug}")
        if settings.emic_user_auth_enabled and PERMISSION_ALL not in principal.permissions:
            if not principal.has_site_access(site.id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Site access denied: {slug}")
        sites.append(site)
    return sites


@router.post("/overview")
async def multi_site_overview(
    body: MultiSiteOverviewRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal: Annotated[Principal, Depends(require_permission("dashboard.read"))],
) -> dict:
    sites = await _resolve_authorized_sites(session, principal, settings, body.site_slugs)
    cache_key = multisite_cache_key([s.slug for s in sites])
    cache = get_cache_service(settings)

    async def build():
        service = MultiSiteAggregationService(session, settings)
        overview = await service.build_overview(sites)
        return overview.to_dict()

    return await cache.get_or_set(cache_key, build, ttl_seconds=MULTISITE_CACHE_TTL)
