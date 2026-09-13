"""Shared pytest hooks for energy-core tests."""

from __future__ import annotations

from sqlalchemy import event, insert, select

from energy_core.db.models import SiteModel, TenantModel
from energy_core.tenancy.bootstrap import DEFAULT_TENANT_NAME, DEFAULT_TENANT_SLUG


@event.listens_for(SiteModel, "before_insert", propagate=True)
def _autofill_site_tenant_id(_mapper, connection, target) -> None:
    """Tests often construct SiteModel directly; attach default tenant when omitted."""
    if target.tenant_id is not None:
        return
    row = connection.execute(
        select(TenantModel.id).where(TenantModel.slug == DEFAULT_TENANT_SLUG)
    ).first()
    if row is None:
        result = connection.execute(
            insert(TenantModel)
            .values(
                name=DEFAULT_TENANT_NAME,
                display_name=DEFAULT_TENANT_NAME,
                slug=DEFAULT_TENANT_SLUG,
                is_active=True,
                status="active",
                timezone="Europe/Stockholm",
                default_currency="SEK",
            )
            .returning(TenantModel.id)
        )
        target.tenant_id = result.scalar_one()
    else:
        target.tenant_id = row[0]
