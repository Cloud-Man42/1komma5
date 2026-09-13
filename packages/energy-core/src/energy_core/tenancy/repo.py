"""Tenant repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from energy_core.db.models import (
    EmicRoleModel,
    EmicUserModel,
    PlatformUserRoleModel,
    SiteModel,
    TenantModel,
    TenantUserModel,
    TenantUserSiteAccessModel,
)


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, tenant_id: int) -> TenantModel | None:
        return await self._session.get(TenantModel, tenant_id)

    async def get_by_slug(self, slug: str) -> TenantModel | None:
        return await self._session.scalar(select(TenantModel).where(TenantModel.slug == slug))

    async def list_active(self) -> list[TenantModel]:
        rows = await self._session.scalars(
            select(TenantModel).where(TenantModel.is_active.is_(True)).order_by(TenantModel.display_name)
        )
        return list(rows)

    async def list_all(self) -> list[TenantModel]:
        rows = await self._session.scalars(select(TenantModel).order_by(TenantModel.display_name))
        return list(rows)

    async def list_for_user(self, user_id: int) -> list[TenantModel]:
        rows = await self._session.scalars(
            select(TenantModel)
            .join(TenantUserModel, TenantUserModel.tenant_id == TenantModel.id)
            .where(TenantUserModel.user_id == user_id, TenantUserModel.is_active.is_(True), TenantModel.is_active.is_(True))
            .order_by(TenantModel.display_name)
        )
        return list(rows)

    async def get_membership(self, tenant_id: int, user_id: int) -> TenantUserModel | None:
        return await self._session.scalar(
            select(TenantUserModel)
            .options(
                selectinload(TenantUserModel.user),
                selectinload(TenantUserModel.roles).selectinload(EmicRoleModel.permissions),
                selectinload(TenantUserModel.site_access),
            )
            .where(TenantUserModel.tenant_id == tenant_id, TenantUserModel.user_id == user_id)
        )

    async def get_membership_by_id(self, tenant_user_id: int) -> TenantUserModel | None:
        return await self._session.scalar(
            select(TenantUserModel)
            .options(
                selectinload(TenantUserModel.user),
                selectinload(TenantUserModel.roles).selectinload(EmicRoleModel.permissions),
                selectinload(TenantUserModel.site_access),
            )
            .where(TenantUserModel.id == tenant_user_id)
        )

    async def list_platform_roles(self, user_id: int) -> frozenset[str]:
        rows = await self._session.scalars(
            select(PlatformUserRoleModel.role_name).where(PlatformUserRoleModel.user_id == user_id)
        )
        return frozenset(rows)

    async def update_tenant(
        self,
        tenant: TenantModel,
        *,
        name: str | None = None,
        display_name: str | None = None,
        timezone: str | None = None,
        default_currency: str | None = None,
        is_active: bool | None = None,
        status: str | None = None,
    ) -> TenantModel:
        if name is not None:
            tenant.name = name
        if display_name is not None:
            tenant.display_name = display_name
        if timezone is not None:
            tenant.timezone = timezone
        if default_currency is not None:
            tenant.default_currency = default_currency
        if is_active is not None:
            tenant.is_active = is_active
        if status is not None:
            tenant.status = status
        await self._session.flush()
        return tenant

    async def create_tenant(
        self,
        *,
        name: str,
        display_name: str,
        slug: str,
        timezone: str = "Europe/Stockholm",
        default_currency: str = "SEK",
    ) -> TenantModel:
        tenant = TenantModel(
            name=name,
            display_name=display_name,
            slug=slug,
            is_active=True,
            status="active",
            timezone=timezone,
            default_currency=default_currency,
        )
        self._session.add(tenant)
        await self._session.flush()
        return tenant

    async def create_membership(self, tenant_id: int, user_id: int) -> TenantUserModel:
        row = TenantUserModel(tenant_id=tenant_id, user_id=user_id, is_active=True)
        self._session.add(row)
        await self._session.flush()
        return row

    async def set_membership_roles(self, tenant_user_id: int, role_ids: list[int]) -> None:
        membership = await self.get_membership_by_id(tenant_user_id)
        if membership is None:
            return
        from energy_core.auth.repos.user_repo import RoleRepository

        role_repo = RoleRepository(self._session)
        membership.roles.clear()
        for role_id in role_ids:
            role = await role_repo.get_by_id(role_id)
            if role is not None:
                membership.roles.append(role)
        await self._session.flush()

    async def set_membership_site_access(self, tenant_user_id: int, site_ids: list[int]) -> None:
        membership = await self.get_membership_by_id(tenant_user_id)
        if membership is None:
            return
        membership.site_access.clear()
        for site_id in site_ids:
            membership.site_access.append(TenantUserSiteAccessModel(tenant_user_id=tenant_user_id, site_id=site_id))
        await self._session.flush()

    async def resolve_membership_site_ids(self, membership: TenantUserModel) -> frozenset[int]:
        return frozenset(row.site_id for row in membership.site_access)

    async def count_sites_for_tenant(self, tenant_id: int) -> int:
        count = await self._session.scalar(
            select(func.count()).select_from(SiteModel).where(SiteModel.tenant_id == tenant_id)
        )
        return int(count or 0)

    async def list_memberships(self, tenant_id: int) -> list[TenantUserModel]:
        rows = await self._session.scalars(
            select(TenantUserModel)
            .options(selectinload(TenantUserModel.user), selectinload(TenantUserModel.roles))
            .where(TenantUserModel.tenant_id == tenant_id)
            .order_by(TenantUserModel.id)
        )
        return list(rows)

    async def delete_membership(self, tenant_id: int, user_id: int) -> bool:
        membership = await self.get_membership(tenant_id, user_id)
        if membership is None:
            return False
        await self._session.delete(membership)
        await self._session.flush()
        return True

    async def delete_tenant(self, tenant: TenantModel) -> None:
        await self._session.delete(tenant)
        await self._session.flush()

    async def find_user_by_email(self, email: str) -> EmicUserModel | None:
        normalized = email.strip().lower()
        return await self._session.scalar(
            select(EmicUserModel).where(func.lower(EmicUserModel.email) == normalized)
        )
