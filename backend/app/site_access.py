"""Site access helpers for authenticated routes."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.user_auth import require_authenticated
from energy_core.auth.permissions import PERMISSION_ALL
from energy_core.auth.principal import Principal
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


async def get_site_for_principal(
    session: AsyncSession,
    principal: Principal,
    slug: str,
    *,
    auth_enabled: bool,
) -> object:
    repo = SiteRepository(session)
    site = await repo.get_by_slug(slug, tenant_id=principal.tenant_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if auth_enabled and PERMISSION_ALL not in principal.permissions and not principal.is_platform_admin:
        if principal.tenant_id is not None and site.tenant_id != principal.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Site access denied")
        if not principal.has_site_access(site.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Site access denied")
    return site


async def filter_sites_for_principal(session: AsyncSession, principal: Principal, *, auth_enabled: bool) -> list:
    repo = SiteRepository(session)
    if principal.tenant_id is not None:
        sites = list(await repo.list_for_tenant(principal.tenant_id))
    else:
        sites = list(await repo.list_all())
    if not auth_enabled or PERMISSION_ALL in principal.permissions or principal.is_platform_admin:
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


def authorized_site(permission: str):
    """FastAPI dependency: resolve site slug with permission + membership checks."""

    async def _dependency(
        slug: str,
        session: Annotated[AsyncSession, Depends(get_db_session)],
        principal: Annotated[Principal, Depends(require_authenticated)],
        settings: Annotated[Settings, Depends(get_app_settings)],
    ):
        return await require_site_with_permission(session, principal, settings, slug, permission)

    return _dependency
