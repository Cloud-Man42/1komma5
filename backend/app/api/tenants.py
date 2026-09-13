"""Tenant workspace API."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.user_auth import SESSION_COOKIE, require_authenticated, verify_csrf
from energy_core.auth.principal import Principal
from energy_core.auth.session_service import SessionService
from energy_core.config import Settings
from energy_core.tenancy.repo import TenantRepository
from energy_core.tenancy.service import TenantContextService
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantSelectRequest(BaseModel):
    tenant_id: int = Field(gt=0)


@router.get("/mine")
async def list_my_tenants(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    principal: Annotated[Principal, Depends(require_authenticated)],
) -> dict:
    tenants = await TenantRepository(session).list_for_user(principal.user_id or 0)
    return {
        "tenants": [
            {
                "id": t.id,
                "slug": t.slug,
                "name": t.name,
                "displayName": t.display_name,
                "status": t.status,
            }
            for t in tenants
        ]
    }


@router.get("/current")
async def get_current_tenant(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal: Annotated[Principal, Depends(require_authenticated)],
) -> dict:
    if principal.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant selection required")
    tenant = await TenantRepository(session).get_by_id(principal.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    membership = await TenantRepository(session).get_membership(tenant.id, principal.user_id or 0)
    return {
        "tenant": {
            "id": tenant.id,
            "slug": tenant.slug,
            "name": tenant.name,
            "displayName": tenant.display_name,
            "status": tenant.status,
        },
        "roles": [r.name for r in membership.roles] if membership else [],
        "permissions": sorted(TenantContextService.membership_permissions(membership)) if membership else [],
        "platformRoles": sorted(principal.platform_roles),
    }


@router.post("/select")
async def select_tenant(
    body: TenantSelectRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal: Annotated[Principal, Depends(require_authenticated)],
) -> dict:
    await verify_csrf(request, session, settings)
    membership = await TenantRepository(session).get_membership(body.tenant_id, principal.user_id or 0)
    if membership is None or not membership.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")

    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    ok = await SessionService(session, settings).set_active_tenant(session_token, body.tenant_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unable to select tenant")
    await session.commit()

    tenant = await TenantRepository(session).get_by_id(body.tenant_id)
    assert tenant is not None
    return {
        "tenant": {
            "id": tenant.id,
            "slug": tenant.slug,
            "name": tenant.name,
            "displayName": tenant.display_name,
        }
    }
