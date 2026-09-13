"""Tenant bootstrap helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import TenantModel

DEFAULT_TENANT_SLUG = "henrik-home"
DEFAULT_TENANT_NAME = "Henrik Home"


async def ensure_default_tenant(session: AsyncSession) -> TenantModel:
    existing = await session.scalar(select(TenantModel).where(TenantModel.slug == DEFAULT_TENANT_SLUG))
    if existing is not None:
        return existing
    tenant = TenantModel(
        name=DEFAULT_TENANT_NAME,
        display_name=DEFAULT_TENANT_NAME,
        slug=DEFAULT_TENANT_SLUG,
        is_active=True,
        status="active",
        timezone="Europe/Stockholm",
        default_currency="SEK",
    )
    session.add(tenant)
    await session.flush()
    return tenant
