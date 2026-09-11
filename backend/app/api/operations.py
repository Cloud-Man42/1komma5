"""Aggregated site operations API."""

from __future__ import annotations

from app.deps import get_app_settings, get_db_session
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from energy_core.platform.modules.site_operations import SiteOperationsService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["operations"])


class OperationsModuleItem(BaseModel):
    module_id: str
    name: str
    module_type: str
    enabled: bool
    runtime_status: str
    health_status: str
    last_error: str | None = None
    device_count: int = 0
    can_disable: bool = True
    onboardable: bool = False
    package_source: str | None = None
    installed_version: str | None = None
    publisher: str | None = None
    package_state: str | None = None
    rollback_available: bool = False
    update_available: bool = False


class OperationsDeviceItem(BaseModel):
    device_type: str
    device_id: int
    name: str
    manufacturer: str
    model: str
    integration: str | None = None
    connection_status: str | None = None
    health_status: str
    last_seen: str | None = None
    enabled: bool = True


class SiteOperationsResponse(BaseModel):
    slug: str
    overall_health_status: str
    modules: list[OperationsModuleItem] = Field(default_factory=list)
    devices: list[OperationsDeviceItem] = Field(default_factory=list)
    integration_health: list[dict] = Field(default_factory=list)


@router.get("/sites/{slug}/operations", response_model=SiteOperationsResponse)
async def get_site_operations(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> SiteOperationsResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    service = SiteOperationsService(session, settings=settings, is_sqlite=settings.is_sqlite)
    snapshot = await service.build_snapshot(site.id, slug)
    return SiteOperationsResponse(
        slug=snapshot.site_slug,
        overall_health_status=snapshot.overall_health_status,
        modules=[
            OperationsModuleItem(
                module_id=item.module_id,
                name=item.name,
                module_type=item.module_type,
                enabled=item.enabled,
                runtime_status=item.runtime_status,
                health_status=item.health_status,
                last_error=item.last_error,
                device_count=item.device_count,
                can_disable=item.can_disable,
                onboardable=item.onboardable,
                package_source=item.package_source,
                installed_version=item.installed_version,
                publisher=item.publisher,
                package_state=item.package_state,
                rollback_available=item.rollback_available,
                update_available=item.update_available,
            )
            for item in snapshot.modules
        ],
        devices=[
            OperationsDeviceItem(
                device_type=item.device_type,
                device_id=item.device_id,
                name=item.name,
                manufacturer=item.manufacturer,
                model=item.model,
                integration=item.integration,
                connection_status=item.connection_status,
                health_status=item.health_status,
                last_seen=item.last_seen,
                enabled=item.enabled,
            )
            for item in snapshot.devices
        ],
        integration_health=list(snapshot.integration_health),
    )
