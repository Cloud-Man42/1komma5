"""EMIC user administration API."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.user_auth import require_permission, verify_csrf
from energy_core.auth.passwords import hash_password, validate_password_policy
from energy_core.auth.repos.auth_audit_repo import AuthAuditRepository
from energy_core.auth.repos.user_repo import RoleRepository, UserRepository
from energy_core.auth.session_service import SessionService
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/users", tags=["users"])


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    role_ids: list[int] = Field(default_factory=list)
    site_ids: list[int] = Field(default_factory=list)
    must_change_password: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("Invalid email")
        return value


class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=64)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    is_active: bool | None = None
    role_ids: list[int] | None = None
    site_ids: list[int] | None = None


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=1, max_length=128)
    must_change_password: bool = True


def _user_item(user, site_map: dict[int, str]) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "displayName": user.display_name,
        "isActive": user.is_active,
        "isLocked": user.is_locked,
        "mustChangePassword": user.must_change_password,
        "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
        "roles": [{"id": r.id, "name": r.name} for r in user.roles],
        "sites": [site_map[s.site_id] for s in user.site_access if s.site_id in site_map],
    }


@router.get("/site-options")
async def list_site_options(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal=Depends(require_permission("users.read")),
) -> dict:
    from energy_core.db.repositories import SiteRepository

    sites = await SiteRepository(session).list_all()
    return {"sites": [{"id": s.id, "slug": s.slug, "name": s.name} for s in sites]}


@router.get("")
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal=Depends(require_permission("users.read")),
) -> dict:
    from energy_core.db.repositories import SiteRepository

    users = await UserRepository(session).list_users()
    site_map = {s.id: s.slug for s in await SiteRepository(session).list_all()}
    return {"users": [_user_item(u, site_map) for u in users]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal=Depends(require_permission("users.create")),
) -> dict:
    await verify_csrf(request, session, settings)
    policy_error = validate_password_policy(body.password)
    if policy_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=policy_error)

    repo = UserRepository(session)
    if await repo.get_by_username_or_email(body.email) or await repo.get_by_username_or_email(body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user = await repo.create_user(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        display_name=body.display_name,
        must_change_password=body.must_change_password,
    )
    if body.role_ids:
        await repo.set_roles(user.id, body.role_ids)
    if body.site_ids:
        await repo.set_site_access(user.id, body.site_ids)

    await AuthAuditRepository(session).append(
        event_type="USER_CREATED",
        action="create_user",
        success=True,
        user_id=principal.user_id,
        username=principal.username,
        entity_type="user",
        entity_id=str(user.id),
        source_ip=request.client.host if request.client else None,
    )
    await session.commit()
    user = await repo.get_by_id(user.id)
    from energy_core.db.repositories import SiteRepository

    site_map = {s.id: s.slug for s in await SiteRepository(session).list_all()}
    return _user_item(user, site_map)


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal=Depends(require_permission("users.update")),
) -> dict:
    await verify_csrf(request, session, settings)
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.is_active is False:
        super_count = await repo.count_active_super_admins(exclude_user_id=user.id)
        role_names = {r.name for r in user.roles}
        if "SUPER_ADMIN" in role_names and super_count == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot disable last SUPER_ADMIN")

    fields = body.model_dump(exclude_none=True, exclude={"role_ids", "site_ids"})
    if fields:
        await repo.update_user(user, **fields)
    if body.role_ids is not None:
        if "SUPER_ADMIN" not in {r.name for r in user.roles}:
            pass
        new_super = False
        role_repo = RoleRepository(session)
        for rid in body.role_ids:
            role = await role_repo.get_by_id(rid)
            if role and role.name == "SUPER_ADMIN":
                new_super = True
        if not new_super:
            super_count = await repo.count_active_super_admins(exclude_user_id=user.id)
            if "SUPER_ADMIN" in {r.name for r in user.roles} and super_count == 0:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot remove last SUPER_ADMIN")
        await repo.set_roles(user.id, body.role_ids)
    if body.site_ids is not None:
        await repo.set_site_access(user.id, body.site_ids)

    await AuthAuditRepository(session).append(
        event_type="USER_UPDATED",
        action="update_user",
        success=True,
        user_id=principal.user_id,
        username=principal.username,
        entity_type="user",
        entity_id=str(user_id),
        source_ip=request.client.host if request.client else None,
    )
    await session.commit()
    user = await repo.get_by_id(user_id)
    from energy_core.db.repositories import SiteRepository

    site_map = {s.id: s.slug for s in await SiteRepository(session).list_all()}
    return _user_item(user, site_map)


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    body: PasswordResetRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal=Depends(require_permission("users.password.reset")),
) -> dict:
    await verify_csrf(request, session, settings)
    policy_error = validate_password_policy(body.new_password)
    if policy_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=policy_error)

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = body.must_change_password
    from datetime import UTC, datetime

    user.password_changed_at = datetime.now(UTC)
    await session.flush()
    await SessionService(session, settings).revoke_all_user_sessions(user.id)

    await AuthAuditRepository(session).append(
        event_type="PASSWORD_RESET",
        action="admin_reset_password",
        success=True,
        user_id=principal.user_id,
        username=principal.username,
        entity_type="user",
        entity_id=str(user_id),
        source_ip=request.client.host if request.client else None,
    )
    await session.commit()
    return {"ok": True}
