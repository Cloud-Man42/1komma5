"""Climate device reading persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.contracts.climate.status import ClimateDeviceState
from energy_core.energy.unified import HvacSection
from energy_core.db.models.climate_device_reading import ClimateDeviceReadingModel


class ClimateStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_reading(
        self,
        *,
        site_id: int,
        module_id: str,
        state: ClimateDeviceState,
    ) -> None:
        payload = {
            "temperature_c": state.temperature_c,
            "humidity_percent": state.humidity_percent,
            "climate_mode": state.climate_mode,
            "target_temperature_c": state.target_temperature_c,
            "online": state.online,
            "source_quality": state.source_quality,
            "vendor": state.vendor,
        }
        row = await self._session.scalar(
            select(ClimateDeviceReadingModel).where(
                ClimateDeviceReadingModel.site_id == site_id,
                ClimateDeviceReadingModel.external_device_id == state.device_id,
            )
        )
        if row is None:
            row = ClimateDeviceReadingModel(
                site_id=site_id,
                module_id=module_id,
                external_device_id=state.device_id,
                display_name=state.display_name,
                payload_json=json.dumps(payload),
                observed_at=state.observed_at,
                stale=state.source_quality == "STALE",
            )
            self._session.add(row)
        else:
            row.module_id = module_id
            row.display_name = state.display_name or row.display_name
            row.payload_json = json.dumps(payload)
            row.observed_at = state.observed_at
            row.stale = state.source_quality in {"STALE", "UNAVAILABLE"}
        await self._session.flush()

    async def list_for_site(self, site_id: int) -> list[ClimateDeviceState]:
        rows = await self._session.scalars(
            select(ClimateDeviceReadingModel).where(ClimateDeviceReadingModel.site_id == site_id)
        )
        result: list[ClimateDeviceState] = []
        for row in rows.all():
            payload = json.loads(row.payload_json)
            result.append(
                ClimateDeviceState(
                    device_id=row.external_device_id,
                    site_id=row.site_id,
                    observed_at=row.observed_at,
                    display_name=row.display_name,
                    temperature_c=payload.get("temperature_c"),
                    humidity_percent=payload.get("humidity_percent"),
                    climate_mode=payload.get("climate_mode"),
                    target_temperature_c=payload.get("target_temperature_c"),
                    online=payload.get("online"),
                    source_quality="STALE" if row.stale else payload.get("source_quality", "LIVE"),
                    vendor=payload.get("vendor"),
                )
            )
        return result

    async def hvac_section_for_site(self, site_id: int) -> HvacSection:
        readings = await self.list_for_site(site_id)
        if not readings:
            return HvacSection()
        online = [reading for reading in readings if reading.online]
        state = "online" if online else "offline"
        return HvacSection(power_kw=None, state=state)

    async def mark_stale_before(self, *, site_id: int, module_id: str, cutoff: datetime) -> None:
        rows = await self._session.scalars(
            select(ClimateDeviceReadingModel).where(
                ClimateDeviceReadingModel.site_id == site_id,
                ClimateDeviceReadingModel.module_id == module_id,
                ClimateDeviceReadingModel.observed_at < cutoff,
            )
        )
        for row in rows.all():
            row.stale = True
        await self._session.flush()
