"""Site access helpers for authenticated routes."""

from __future__ import annotations

from energy_core.auth.permissions import PERMISSION_ALL
from energy_core.auth.principal import Principal
from energy_core.db.repositories import SiteRepository
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


async def get_site_for_principal(
    session: AsyncSession,
    principal: Principal,
    slug: str,
    *,
    auth_enabled: bool,
) -> object:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if auth_enabled and PERMISSION_ALL not in principal.permissions:
        if not principal.has_site_access(site.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Site access denied")
    return site


async def filter_sites_for_principal(session: AsyncSession, principal: Principal, *, auth_enabled: bool) -> list:
    sites = list(await SiteRepository(session).list_all())
    if not auth_enabled or PERMISSION_ALL in principal.permissions:
        return sites
    allowed = principal.site_ids
    return [s for s in sites if s.id in allowed]


async def require_site_with_permission(
    session: AsyncSession,
    principal: Principal,
    settings,
    slug: str,
    permission: str,
):
    """Resolve a site by slug after permission + site membership checks."""
    if getattr(settings, "emic_user_auth_enabled", False) and not principal.has_permission(permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return await get_site_for_principal(session, principal, slug, auth_enabled=settings.emic_user_auth_enabled)
