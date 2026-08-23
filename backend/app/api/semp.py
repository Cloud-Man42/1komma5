"""SEMP HTTP endpoints for Virtual EVSE discovery and status."""

from __future__ import annotations

from app.deps import get_db_session
from energy_core.db.models import EvChargerModel
from energy_core.virtual_evse.device_profile import VirtualEvseDeviceProfile
from energy_core.virtual_evse.from_charger import virtual_evse_state_from_charger
from energy_core.virtual_evse.semp_payloads import (
    build_device2em,
    build_device_info,
    build_device_list,
    build_device_status,
)
from energy_core.virtual_evse.store import GLOBAL_VIRTUAL_EVSE_STORE
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["semp"])


def _resolve_state(charger: EvChargerModel):
    runtime = GLOBAL_VIRTUAL_EVSE_STORE.get(charger.id)
    if runtime is not None:
        return runtime
    return virtual_evse_state_from_charger(charger)


async def _enabled_chargers(session: AsyncSession) -> list[EvChargerModel]:
    result = await session.execute(
        select(EvChargerModel).where(EvChargerModel.virtual_evse_enabled.is_(True))
    )
    return list(result.scalars().all())


async def _charger_for_device(session: AsyncSession, device_id: str) -> EvChargerModel:
    charger_id = GLOBAL_VIRTUAL_EVSE_STORE.resolve_charger_id(device_id)
    if charger_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown SEMP device")
    result = await session.execute(select(EvChargerModel).where(EvChargerModel.id == charger_id))
    charger = result.scalar_one_or_none()
    if charger is None or not charger.virtual_evse_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown SEMP device")
    return charger


@router.get("/semp")
async def list_semp_devices(session: AsyncSession = Depends(get_db_session)) -> dict:
    chargers = await _enabled_chargers(session)
    device_ids = [f"emic-evse-{c.id}" for c in chargers]
    return build_device_list(device_ids)


@router.get("/semp/{device_id}")
async def get_semp_device(device_id: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    charger = await _charger_for_device(session, device_id)
    profile = VirtualEvseDeviceProfile.for_charger(
        charger.id,
        max_power_w=charger.max_power_w or 11000.0,
        name=charger.name,
    )
    return build_device_info(profile)


@router.get("/semp/{device_id}/DeviceStatus")
async def get_semp_device_status(
    device_id: str, session: AsyncSession = Depends(get_db_session)
) -> dict:
    charger = await _charger_for_device(session, device_id)
    state = _resolve_state(charger)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Virtual EVSE state unavailable"
        )
    return build_device_status(state)


@router.get("/semp/{device_id}/Device2EM")
async def get_semp_device2em(
    device_id: str, session: AsyncSession = Depends(get_db_session)
) -> dict:
    charger = await _charger_for_device(session, device_id)
    state = _resolve_state(charger)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Virtual EVSE state unavailable"
        )
    return build_device2em(state)
