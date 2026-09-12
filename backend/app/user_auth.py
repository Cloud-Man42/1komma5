"""EMIC user authentication and authorization dependencies."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from energy_core.auth.principal import Principal, break_glass_principal, legacy_open_principal
from energy_core.auth.repos.user_repo import UserRepository
from energy_core.auth.session_service import SessionService
from energy_core.config import Settings
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

_bearer = HTTPBearer(auto_error=False)

SESSION_COOKIE = "emic_session"
CSRF_COOKIE = "emic_csrf"
CSRF_HEADER = "X-CSRF-Token"


def _session_token_from_request(request: Request) -> str | None:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        return cookie
    return None


async def resolve_principal(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
) -> Principal | None:
    if not settings.emic_user_auth_enabled:
        expected = (settings.emic_admin_token or "").strip()
        if expected:
            if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials == expected:
                return break_glass_principal()
            return legacy_open_principal()
        return legacy_open_principal()

    expected = (settings.emic_admin_token or "").strip()
    if expected and credentials and credentials.scheme.lower() == "bearer":
        if credentials.credentials == expected:
            return break_glass_principal()

    token = _session_token_from_request(request)
    if token:
        principal = await SessionService(session, settings).resolve_principal(token)
        if principal is not None:
            return principal

    if not expected:
        return legacy_open_principal()
    return None


async def get_optional_principal(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal | None:
    return await resolve_principal(request, session, settings, credentials)


async def require_authenticated(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Principal:
    if not settings.emic_user_auth_enabled:
        return principal or legacy_open_principal()
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return principal


def require_permission(permission: str):
    async def _dep(
        principal: Annotated[Principal, Depends(require_authenticated)],
        settings: Annotated[Settings, Depends(get_app_settings)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    ) -> Principal:
        if settings.emic_user_auth_enabled:
            if not principal.has_permission(permission):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
            return principal
        expected = (settings.emic_admin_token or "").strip()
        if expected:
            if credentials is None or credentials.scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Admin token required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if credentials.credentials != expected:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid admin token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return principal

    return _dep


def require_site_permission(permission: str):
    """Factory for route deps that require permission + site slug access."""

    async def _dep(
        slug: str,
        principal: Annotated[Principal, Depends(require_permission(permission))],
        session: Annotated[AsyncSession, Depends(get_db_session)],
        settings: Annotated[Settings, Depends(get_app_settings)],
    ) -> tuple[Principal, object]:
        from app.site_access import require_site_with_permission

        site = await require_site_with_permission(session, principal, settings, slug, permission)
        return principal, site

    return _dep


async def require_site_access(
    principal: Principal,
    *,
    site_id: int,
    settings: Settings,
) -> None:
    if not settings.emic_user_auth_enabled:
        return
    if not principal.has_site_access(site_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Site access denied")


async def verify_csrf(
    request: Request,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not settings.emic_user_auth_enabled:
        return
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    token = _session_token_from_request(request)
    if not token:
        return
    csrf = request.headers.get(CSRF_HEADER) or request.cookies.get(CSRF_COOKIE)
    if not await SessionService(session, settings).verify_csrf(token, csrf):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


async def build_user_response(session: AsyncSession, principal: Principal) -> dict:
    site_slugs: list[str] = []
    if principal.user_id is not None:
        user = await UserRepository(session).get_by_id(principal.user_id)
        if user is not None:
            from energy_core.db.repositories import SiteRepository

            sites = await SiteRepository(session).list_all()
            site_map = {s.id: s.slug for s in sites}
            site_slugs = [site_map[sid] for sid in sorted(principal.site_ids) if sid in site_map]
    return {
        "id": principal.user_id,
        "username": principal.username,
        "email": principal.email,
        "displayName": principal.display_name,
        "roles": sorted(principal.roles),
        "permissions": sorted(p for p in principal.permissions if p != "*"),
        "sites": site_slugs,
        "mustChangePassword": principal.must_change_password,
        "authMethod": principal.auth_method.value,
    }
