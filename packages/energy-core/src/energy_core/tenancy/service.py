"""Tenant context resolution."""

from __future__ import annotations

from energy_core.auth.permissions import PERMISSION_ALL, permission_grants
from energy_core.auth.principal import Principal
from energy_core.config import Settings
from energy_core.db.models import EmicUserSessionModel
from energy_core.tenancy.context import TenantContext
from energy_core.tenancy.repo import TenantRepository
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class TenantContextService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._tenants = TenantRepository(session)

    async def resolve_for_principal(
        self,
        principal: Principal,
        *,
        session_row: EmicUserSessionModel | None = None,
        requested_tenant_id: int | None = None,
    ) -> TenantContext:
        if principal.user_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context requires authenticated user")

        platform_roles = await self._tenants.list_platform_roles(principal.user_id)
        is_platform_admin = "PLATFORM_SUPER_ADMIN" in platform_roles or principal.is_super_admin

        tenant_id = requested_tenant_id
        if tenant_id is None and session_row is not None:
            tenant_id = session_row.active_tenant_id

        memberships = await self._tenants.list_for_user(principal.user_id)
        if tenant_id is None and len(memberships) == 1:
            tenant_id = memberships[0].id

        if tenant_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant selection required")

        if requested_tenant_id is not None and not is_platform_admin:
            allowed_ids = {t.id for t in memberships}
            if tenant_id not in allowed_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")

        tenant = await self._tenants.get_by_id(tenant_id)
        if tenant is None or not tenant.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not available")

        membership = await self._tenants.get_membership(tenant_id, principal.user_id)
        if membership is None or not membership.is_active:
            if not is_platform_admin:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")

        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")

        return TenantContext(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            tenant_name=tenant.name,
            tenant_display_name=tenant.display_name,
            user_id=principal.user_id,
            tenant_user_id=membership.id,
            is_platform_admin=is_platform_admin,
            platform_roles=platform_roles,
        )

    @staticmethod
    def membership_permissions(membership) -> frozenset[str]:
        perms: set[str] = set()
        for role in membership.roles:
            for perm in role.permissions:
                perms.add(perm.key)
        return frozenset(perms)

    @staticmethod
    def has_tenant_permission(context: TenantContext, membership, permission: str) -> bool:
        if context.is_platform_admin:
            return True
        return permission_grants(permission, TenantContextService.membership_permissions(membership))
