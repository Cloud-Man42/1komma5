"""User, role, and site access repositories."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.auth.normalize import normalize_email, normalize_username
from energy_core.auth.permissions import PERMISSION_ALL, ROLE_PERMISSIONS
from energy_core.db.models import (
    EmicPermissionModel,
    EmicRoleModel,
    EmicRolePermissionModel,
    EmicUserModel,
    EmicUserRoleModel,
    EmicUserSiteAccessModel,
)
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_users(self) -> int:
        return int(await self._session.scalar(select(func.count()).select_from(EmicUserModel)) or 0)

    async def get_by_id(self, user_id: int) -> EmicUserModel | None:
        return await self._session.get(
            EmicUserModel,
            user_id,
            options=[
                selectinload(EmicUserModel.roles).selectinload(EmicRoleModel.permissions),
                selectinload(EmicUserModel.site_access),
            ],
        )

    async def get_by_username_or_email(self, username_or_email: str) -> EmicUserModel | None:
        normalized = normalize_email(username_or_email) if "@" in username_or_email else normalize_username(username_or_email)
        stmt = (
            select(EmicUserModel)
            .options(
                selectinload(EmicUserModel.roles).selectinload(EmicRoleModel.permissions),
                selectinload(EmicUserModel.site_access),
            )
            .where(
                (EmicUserModel.email_normalized == normalized) | (EmicUserModel.username_normalized == normalized)
            )
        )
        return await self._session.scalar(stmt)

    async def list_users(self) -> tuple[EmicUserModel, ...]:
        rows = await self._session.scalars(
            select(EmicUserModel)
            .options(
                selectinload(EmicUserModel.roles),
                selectinload(EmicUserModel.site_access),
            )
            .order_by(EmicUserModel.display_name, EmicUserModel.username)
        )
        return tuple(rows.all())

    async def create_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
        must_change_password: bool = False,
    ) -> EmicUserModel:
        user = EmicUserModel(
            username=username.strip(),
            username_normalized=normalize_username(username),
            email=email.strip(),
            email_normalized=normalize_email(email),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name or username.strip(),
            must_change_password=must_change_password,
            password_changed_at=datetime.now(UTC),
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_user(self, user: EmicUserModel, **fields: object) -> EmicUserModel:
        for key, value in fields.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        if "email" in fields and fields["email"] is not None:
            user.email_normalized = normalize_email(str(fields["email"]))
        if "username" in fields and fields["username"] is not None:
            user.username_normalized = normalize_username(str(fields["username"]))
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        return user

    async def set_roles(self, user_id: int, role_ids: list[int]) -> None:
        await self._session.execute(delete(EmicUserRoleModel).where(EmicUserRoleModel.user_id == user_id))
        for role_id in role_ids:
            self._session.add(EmicUserRoleModel(user_id=user_id, role_id=role_id))
        await self._session.flush()

    async def set_site_access(self, user_id: int, site_ids: list[int]) -> None:
        await self._session.execute(delete(EmicUserSiteAccessModel).where(EmicUserSiteAccessModel.user_id == user_id))
        for site_id in site_ids:
            self._session.add(EmicUserSiteAccessModel(user_id=user_id, site_id=site_id))
        await self._session.flush()

    async def record_failed_login(self, user: EmicUserModel, *, lockout_until: datetime | None) -> None:
        user.failed_login_attempts += 1
        user.last_login_at = datetime.now(UTC)
        if lockout_until is not None:
            user.is_locked = True
            user.lockout_until = lockout_until
        await self._session.flush()

    async def record_successful_login(self, user: EmicUserModel) -> None:
        now = datetime.now(UTC)
        user.failed_login_attempts = 0
        user.is_locked = False
        user.lockout_until = None
        user.last_login_at = now
        user.last_successful_login_at = now
        await self._session.flush()

    async def count_active_super_admins(self, *, exclude_user_id: int | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(EmicUserRoleModel)
            .join(EmicRoleModel, EmicRoleModel.id == EmicUserRoleModel.role_id)
            .join(EmicUserModel, EmicUserModel.id == EmicUserRoleModel.user_id)
            .where(EmicRoleModel.name == "SUPER_ADMIN", EmicUserModel.is_active.is_(True))
        )
        if exclude_user_id is not None:
            stmt = stmt.where(EmicUserModel.id != exclude_user_id)
        return int(await self._session.scalar(stmt) or 0)

    def resolve_permissions(self, user: EmicUserModel) -> frozenset[str]:
        keys: set[str] = set()
        for role in user.roles:
            if role.name in ROLE_PERMISSIONS:
                keys.update(ROLE_PERMISSIONS[role.name])
            for perm in role.permissions:
                keys.add(perm.key)
        if PERMISSION_ALL in keys:
            return frozenset({PERMISSION_ALL})
        return frozenset(keys)

    def resolve_site_ids(self, user: EmicUserModel) -> frozenset[int]:
        return frozenset(row.site_id for row in user.site_access)


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> EmicRoleModel | None:
        return await self._session.scalar(select(EmicRoleModel).where(EmicRoleModel.name == name))

    async def list_roles(self) -> tuple[EmicRoleModel, ...]:
        rows = await self._session.scalars(
            select(EmicRoleModel)
            .options(selectinload(EmicRoleModel.permissions))
            .order_by(EmicRoleModel.name)
        )
        return tuple(rows.all())

    async def get_by_id(self, role_id: int) -> EmicRoleModel | None:
        return await self._session.scalar(
            select(EmicRoleModel)
            .options(selectinload(EmicRoleModel.permissions))
            .where(EmicRoleModel.id == role_id)
        )

    async def create_role(self, *, name: str, description: str | None, is_system_role: bool = False) -> EmicRoleModel:
        role = EmicRoleModel(name=name, description=description, is_system_role=is_system_role)
        self._session.add(role)
        await self._session.flush()
        return role

    async def set_permissions(self, role_id: int, permission_ids: list[int]) -> None:
        await self._session.execute(
            delete(EmicRolePermissionModel).where(EmicRolePermissionModel.role_id == role_id)
        )
        for permission_id in permission_ids:
            self._session.add(EmicRolePermissionModel(role_id=role_id, permission_id=permission_id))
        await self._session.flush()

    async def delete_role(self, role: EmicRoleModel) -> None:
        await self._session.delete(role)
        await self._session.flush()


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> tuple[EmicPermissionModel, ...]:
        rows = await self._session.scalars(select(EmicPermissionModel).order_by(EmicPermissionModel.group_name, EmicPermissionModel.key))
        return tuple(rows.all())

    async def get_by_key(self, key: str) -> EmicPermissionModel | None:
        return await self._session.scalar(select(EmicPermissionModel).where(EmicPermissionModel.key == key))

    async def get_by_keys(self, keys: list[str]) -> tuple[EmicPermissionModel, ...]:
        if not keys:
            return ()
        rows = await self._session.scalars(select(EmicPermissionModel).where(EmicPermissionModel.key.in_(keys)))
        return tuple(rows.all())
