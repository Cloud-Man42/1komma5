"""Idempotent RBAC seed (roles, permissions, mappings)."""

from __future__ import annotations

from energy_core.auth.permissions import PERMISSION_CATALOG, ROLE_PERMISSIONS, SYSTEM_ROLES
from energy_core.auth.repos.user_repo import PermissionRepository, RoleRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_rbac_seed(session: AsyncSession) -> None:
    perm_repo = PermissionRepository(session)
    role_repo = RoleRepository(session)

    key_to_id: dict[str, int] = {}
    for perm_def in PERMISSION_CATALOG:
        existing = await perm_repo.get_by_key(perm_def.key)
        if existing is None:
            from energy_core.db.models import EmicPermissionModel

            row = EmicPermissionModel(
                key=perm_def.key,
                name=perm_def.name,
                description=perm_def.description,
                group_name=perm_def.group_name,
            )
            session.add(row)
            await session.flush()
            key_to_id[perm_def.key] = row.id
        else:
            key_to_id[perm_def.key] = existing.id

    for role_name in SYSTEM_ROLES:
        role = await role_repo.get_by_name(role_name)
        if role is None:
            role = await role_repo.create_role(
                name=role_name,
                description=f"System role {role_name}",
                is_system_role=True,
            )
        perm_keys = ROLE_PERMISSIONS.get(role_name, frozenset())
        if "*" in perm_keys:
            permission_ids = list(key_to_id.values())
        else:
            permission_ids = [key_to_id[k] for k in perm_keys if k in key_to_id]
        await role_repo.set_permissions(role.id, permission_ids)
