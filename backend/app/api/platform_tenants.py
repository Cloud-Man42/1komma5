"""Platform-admin tenant CRUD."""

from __future__ import annotations

import re
from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.user_auth import require_platform_admin, verify_csrf
from energy_core.auth.principal import Principal
from energy_core.config import Settings
from energy_core.db.models import TenantModel
from energy_core.tenancy.bootstrap import DEFAULT_TENANT_SLUG
from energy_core.tenancy.repo import TenantRepository
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/platform/tenants", tags=["platform-tenants"])

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(value: str) -> str:
    slug = value.strip().lower()
    if not _SLUG_RE.fullmatch(slug):
        raise ValueError("Slug may only contain a-z, 0-9 and hyphens.")
    return slug


def _tenant_payload(tenant: TenantModel) -> dict:
    return {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "displayName": tenant.display_name,
        "status": tenant.status,
        "isActive": tenant.is_active,
        "timezone": tenant.timezone,
        "defaultCurrency": tenant.default_currency,
    }


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=2, max_length=64)
    timezone: str = Field(default="Europe/Stockholm", min_length=1, max_length=64)
    default_currency: str = Field(default="SEK", min_length=3, max_length=8)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return _validate_slug(value)

    @field_validator("name", "display_name", "timezone", "default_currency", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TenantMemberAddRequest(BaseModel):
    email: str = Field(min_length=3, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    default_currency: str | None = Field(default=None, min_length=3, max_length=8)
    is_active: bool | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("name", "display_name", "timezone", "default_currency", "status", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


@router.get("")
async def list_platform_tenants(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> dict:
    tenants = await TenantRepository(session).list_all()
    return {"tenants": [_tenant_payload(t) for t in tenants]}


@router.get("/{tenant_id}")
async def get_platform_tenant(
    tenant_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> dict:
    tenant = await TenantRepository(session).get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"tenant": _tenant_payload(tenant)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_platform_tenant(
    body: TenantCreateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> dict:
    await verify_csrf(request, session, settings)
    repo = TenantRepository(session)
    if await repo.get_by_slug(body.slug) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")
    tenant = await repo.create_tenant(
        name=body.name,
        display_name=body.display_name,
        slug=body.slug,
        timezone=body.timezone,
        default_currency=body.default_currency,
    )
    await session.commit()
    return {"tenant": _tenant_payload(tenant)}


@router.patch("/{tenant_id}")
async def update_platform_tenant(
    tenant_id: int,
    body: TenantUpdateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> dict:
    await verify_csrf(request, session, settings)
    repo = TenantRepository(session)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")

    if body.is_active is False and body.status is None:
        updates["status"] = "disabled"
    elif body.is_active is True and body.status is None and tenant.status == "disabled":
        updates["status"] = "active"

    tenant = await repo.update_tenant(tenant, **updates)
    await session.commit()
    return {"tenant": _tenant_payload(tenant)}


def _member_payload(membership) -> dict:
    user = membership.user
    return {
        "tenantUserId": membership.id,
        "userId": membership.user_id,
        "email": user.email if user is not None else "",
        "displayName": user.display_name if user is not None else "",
        "isActive": membership.is_active,
        "roles": [role.name for role in membership.roles],
    }


@router.get("/{tenant_id}/members")
async def list_platform_tenant_members(
    tenant_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> dict:
    repo = TenantRepository(session)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    members = await repo.list_memberships(tenant_id)
    return {"members": [_member_payload(member) for member in members]}


@router.post("/{tenant_id}/members", status_code=status.HTTP_201_CREATED)
async def add_platform_tenant_member(
    tenant_id: int,
    body: TenantMemberAddRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> dict:
    await verify_csrf(request, session, settings)
    repo = TenantRepository(session)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant is disabled")

    user = await repo.find_user_by_email(body.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = await repo.get_membership(tenant_id, user.id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already in tenant")

    membership = await repo.create_membership(tenant_id, user.id)
    await session.commit()
    membership = await repo.get_membership_by_id(membership.id)
    assert membership is not None
    return {"member": _member_payload(membership)}


@router.delete("/{tenant_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_platform_tenant_member(
    tenant_id: int,
    user_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> None:
    await verify_csrf(request, session, settings)
    repo = TenantRepository(session)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not await repo.delete_membership(tenant_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    await session.commit()


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_tenant(
    tenant_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal: Annotated[Principal, Depends(require_platform_admin)],
) -> None:
    await verify_csrf(request, session, settings)
    repo = TenantRepository(session)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant.slug == DEFAULT_TENANT_SLUG:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Default tenant cannot be deleted")
    if await repo.count_sites_for_tenant(tenant_id) > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant has sites")
    await repo.delete_tenant(tenant)
    await session.commit()
