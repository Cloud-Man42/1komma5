"""EMIC role administration API."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.user_auth import require_permission, verify_csrf
from energy_core.auth.repos.user_repo import PermissionRepository, RoleRepository
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/roles", tags=["roles"])


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    description: str | None = None
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    description: str | None = None
    permission_ids: list[int] | None = None


@router.get("")
async def list_roles(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal=Depends(require_permission("roles.read")),
) -> dict:
    roles = await RoleRepository(session).list_roles()
    return {
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "isSystemRole": r.is_system_role,
                "permissions": [{"id": p.id, "key": p.key, "name": p.name} for p in r.permissions],
            }
            for r in roles
        ]
    }


@router.get("/permissions")
async def list_permissions(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal=Depends(require_permission("roles.read")),
) -> dict:
    perms = await PermissionRepository(session).list_all()
    return {
        "permissions": [
            {"id": p.id, "key": p.key, "name": p.name, "description": p.description, "group": p.group_name}
            for p in perms
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal=Depends(require_permission("roles.manage")),
) -> dict:
    await verify_csrf(request, session, settings)
    repo = RoleRepository(session)
    if await repo.get_by_name(body.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")
    role = await repo.create_role(name=body.name, description=body.description, is_system_role=False)
    if body.permission_ids:
        await repo.set_permissions(role.id, body.permission_ids)
    await session.commit()
    role = await repo.get_by_id(role.id)
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "isSystemRole": role.is_system_role,
        "permissions": [{"id": p.id, "key": p.key} for p in role.permissions],
    }


@router.patch("/{role_id}")
async def update_role(
    role_id: int,
    body: RoleUpdateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal=Depends(require_permission("roles.manage")),
) -> dict:
    await verify_csrf(request, session, settings)
    repo = RoleRepository(session)
    role = await repo.get_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if body.description is not None:
        role.description = body.description
    if body.permission_ids is not None:
        await repo.set_permissions(role.id, body.permission_ids)
    await session.commit()
    role = await repo.get_by_id(role_id)
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "isSystemRole": role.is_system_role,
        "permissions": [{"id": p.id, "key": p.key} for p in role.permissions],
    }


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    _principal=Depends(require_permission("roles.manage")),
) -> None:
    await verify_csrf(request, session, settings)
    repo = RoleRepository(session)
    role = await repo.get_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete system role")
    await repo.delete_role(role)
    await session.commit()
