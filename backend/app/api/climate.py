"""Generic climate device API (vendor-neutral)."""

from __future__ import annotations

from app.deps import get_app_settings, get_db_session
from app.site_access import require_site_with_permission
from app.user_auth import require_authenticated
from energy_core.auth.principal import Principal
from energy_core.climate.repository import ClimateStateRepository
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/sites", tags=["climate"])


@router.get("/{slug}/climate/devices")
async def list_climate_devices(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_authenticated),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    site = await require_site_with_permission(session, principal, settings, slug, "integration.read")
    readings = await ClimateStateRepository(session).list_for_site(site.id)
    return {
        "site_slug": slug,
        "devices": [
            {
                "device_id": r.device_id,
                "display_name": r.display_name,
                "temperature_c": r.temperature_c,
                "humidity_percent": r.humidity_percent,
                "climate_mode": r.climate_mode,
                "target_temperature_c": r.target_temperature_c,
                "online": r.online,
                "source_quality": r.source_quality,
                "observed_at": r.observed_at.isoformat(),
                "vendor": r.vendor,
            }
            for r in readings
        ],
    }


@router.get("/{slug}/climate/devices/{device_id}")
async def get_climate_device(
    slug: str,
    device_id: str,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_authenticated),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    site = await require_site_with_permission(session, principal, settings, slug, "integration.read")
    readings = await ClimateStateRepository(session).list_for_site(site.id)
    for reading in readings:
        if reading.device_id == device_id:
            return {
                "device_id": reading.device_id,
                "display_name": reading.display_name,
                "temperature_c": reading.temperature_c,
                "humidity_percent": reading.humidity_percent,
                "climate_mode": reading.climate_mode,
                "target_temperature_c": reading.target_temperature_c,
                "online": reading.online,
                "source_quality": reading.source_quality,
                "observed_at": reading.observed_at.isoformat(),
                "vendor": reading.vendor,
            }
    raise HTTPException(status_code=404, detail="Climate device not found")
