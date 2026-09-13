"""Sync legacy user RBAC into tenant-scoped membership tables."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    EmicRoleModel,
    EmicUserModel,
    EmicUserRoleModel,
    EmicUserSiteAccessModel,
    PlatformUserRoleModel,
    SiteModel,
    TenantUserModel,
    TenantUserRoleModel,
    TenantUserSiteAccessModel,
)
from energy_core.tenancy.bootstrap import ensure_default_tenant


async def sync_tenant_memberships_for_default_tenant(session: AsyncSession) -> None:
    tenant = await ensure_default_tenant(session)

    for site in await session.scalars(select(SiteModel)):
        if site.tenant_id is None:
            site.tenant_id = tenant.id

    users = list(await session.scalars(select(EmicUserModel)))
    for user in users:
        membership = await session.scalar(
            select(TenantUserModel).where(
                TenantUserModel.tenant_id == tenant.id,
                TenantUserModel.user_id == user.id,
            )
        )
        if membership is None:
            membership = TenantUserModel(tenant_id=tenant.id, user_id=user.id, is_active=user.is_active)
            session.add(membership)
            await session.flush()

        for role_id in await session.scalars(
            select(EmicUserRoleModel.role_id).where(EmicUserRoleModel.user_id == user.id)
        ):
            exists = await session.scalar(
                select(TenantUserRoleModel.role_id).where(
                    TenantUserRoleModel.tenant_user_id == membership.id,
                    TenantUserRoleModel.role_id == role_id,
                )
            )
            if exists is None:
                session.add(TenantUserRoleModel(tenant_user_id=membership.id, role_id=role_id))

        for site_id in await session.scalars(
            select(EmicUserSiteAccessModel.site_id).where(EmicUserSiteAccessModel.user_id == user.id)
        ):
            exists = await session.scalar(
                select(TenantUserSiteAccessModel.id).where(
                    TenantUserSiteAccessModel.tenant_user_id == membership.id,
                    TenantUserSiteAccessModel.site_id == site_id,
                )
            )
            if exists is None:
                session.add(TenantUserSiteAccessModel(tenant_user_id=membership.id, site_id=site_id))

        is_super = await session.scalar(
            select(EmicRoleModel.id)
            .join(EmicUserRoleModel, EmicUserRoleModel.role_id == EmicRoleModel.id)
            .where(EmicUserRoleModel.user_id == user.id, EmicRoleModel.name == "SUPER_ADMIN")
        )
        if is_super is not None:
            exists = await session.scalar(
                select(PlatformUserRoleModel.id).where(
                    PlatformUserRoleModel.user_id == user.id,
                    PlatformUserRoleModel.role_name == "PLATFORM_SUPER_ADMIN",
                )
            )
            if exists is None:
                session.add(PlatformUserRoleModel(user_id=user.id, role_name="PLATFORM_SUPER_ADMIN"))

    await session.flush()
