"""Generic climate device API (vendor-neutral)."""

from __future__ import annotations

from app.deps import get_db_session
from energy_core.climate.repository import ClimateStateRepository
from energy_core.db.repositories import SiteRepository
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/sites", tags=["climate"])


@router.get("/{slug}/climate/devices")
async def list_climate_devices(slug: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
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
async def get_climate_device(slug: str, device_id: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
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
