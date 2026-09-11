"""Site device registry API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from energy_core.db.repositories import SiteRepository
from energy_core.platform.devices.registry import DeviceRegistry, DeviceType

router = APIRouter(tags=["devices"])


class DeviceRecordResponse(BaseModel):
    device_type: str
    device_id: int
    name: str
    manufacturer: str
    model: str
    integration: str | None = None
    connection_status: str | None = None
    health_status: str
    last_seen: str | None = None
    enabled: bool
    metadata: dict = Field(default_factory=dict)


class SiteDevicesResponse(BaseModel):
    slug: str
    devices: list[DeviceRecordResponse] = Field(default_factory=list)


class SiteDeviceDetailResponse(DeviceRecordResponse):
    slug: str
    configuration_status: str = "unknown"


def _serialize_device(record) -> DeviceRecordResponse:
    return DeviceRecordResponse(
        device_type=record.device_id.device_type.value,
        device_id=record.device_id.id,
        name=record.name,
        manufacturer=record.manufacturer,
        model=record.model,
        integration=record.integration,
        connection_status=record.connection_status,
        health_status=record.health_status.value,
        last_seen=record.last_seen.isoformat() if record.last_seen else None,
        enabled=record.enabled,
        metadata=dict(record.metadata),
    )


@router.get("/sites/{slug}/devices", response_model=SiteDevicesResponse)
async def list_site_devices(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> SiteDevicesResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    records = await DeviceRegistry(session).list_for_site(site.id)
    return SiteDevicesResponse(
        slug=slug,
        devices=[_serialize_device(record) for record in records],
    )


@router.get("/sites/{slug}/devices/{device_type}/{device_id}", response_model=SiteDeviceDetailResponse)
async def get_site_device(
    slug: str,
    device_type: str,
    device_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SiteDeviceDetailResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    record = await DeviceRegistry(session).get_for_site(site.id, device_type, device_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    base = _serialize_device(record)
    configuration_status = "active" if record.enabled else "disabled"
    return SiteDeviceDetailResponse(
        slug=slug,
        configuration_status=configuration_status,
        **base.model_dump(),
    )
