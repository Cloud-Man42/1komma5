"""Energy balance snapshot persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EnergyBalanceSnapshotModel, SiteEnergyConfigModel


@dataclass(frozen=True, slots=True)
class SiteEnergyConfig:
    site_id: int
    load_includes_ev_charger: bool | None
    inverter_display_name: str
    physical_ev_charger_label: str
    ev_vehicle_label: str


class SiteEnergyConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, site_id: int) -> SiteEnergyConfig:
        result = await self._session.execute(
            select(SiteEnergyConfigModel).where(SiteEnergyConfigModel.site_id == site_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = SiteEnergyConfigModel(site_id=site_id)
            self._session.add(row)
            await self._session.flush()
        return self._to_config(row)

    async def update(
        self,
        site_id: int,
        *,
        load_includes_ev_charger: bool | None = None,
        clear_load_includes_ev_charger: bool = False,
        inverter_display_name: str | None = None,
        physical_ev_charger_label: str | None = None,
        ev_vehicle_label: str | None = None,
    ) -> SiteEnergyConfig:
        result = await self._session.execute(
            select(SiteEnergyConfigModel).where(SiteEnergyConfigModel.site_id == site_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = SiteEnergyConfigModel(site_id=site_id)
            self._session.add(row)
        if clear_load_includes_ev_charger:
            row.load_includes_ev_charger = None
        elif load_includes_ev_charger is not None:
            row.load_includes_ev_charger = load_includes_ev_charger
        if inverter_display_name is not None:
            row.inverter_display_name = inverter_display_name.strip() or row.inverter_display_name
        if physical_ev_charger_label is not None:
            row.physical_ev_charger_label = physical_ev_charger_label.strip() or row.physical_ev_charger_label
        if ev_vehicle_label is not None:
            row.ev_vehicle_label = ev_vehicle_label.strip() or row.ev_vehicle_label
        await self._session.flush()
        return self._to_config(row)

    def _to_config(self, row: SiteEnergyConfigModel) -> SiteEnergyConfig:
        return SiteEnergyConfig(
            site_id=row.site_id,
            load_includes_ev_charger=row.load_includes_ev_charger,
            inverter_display_name=row.inverter_display_name,
            physical_ev_charger_label=row.physical_ev_charger_label,
            ev_vehicle_label=row.ev_vehicle_label,
        )


@dataclass(frozen=True, slots=True)
class StoredEnergyBalanceSnapshot:
    id: int
    site_id: int
    charger_id: int
    recorded_at: datetime
    status: str
    flags: list[str]
    payload: dict


class EnergyBalanceRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def insert_snapshot(
        self,
        *,
        site_id: int,
        charger_id: int,
        recorded_at: datetime,
        status: str,
        flags: list[str],
        payload: str,
    ) -> None:
        self._session.add(
            EnergyBalanceSnapshotModel(
                site_id=site_id,
                charger_id=charger_id,
                recorded_at=recorded_at,
                status=status,
                flags_json=json.dumps(flags),
                snapshot_json=payload,
            )
        )

    async def get_latest(self, *, site_id: int, charger_id: int) -> StoredEnergyBalanceSnapshot | None:
        result = await self._session.execute(
            select(EnergyBalanceSnapshotModel)
            .where(
                EnergyBalanceSnapshotModel.site_id == site_id,
                EnergyBalanceSnapshotModel.charger_id == charger_id,
            )
            .order_by(desc(EnergyBalanceSnapshotModel.recorded_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_stored(row)

    async def list_history(
        self,
        *,
        site_id: int,
        charger_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StoredEnergyBalanceSnapshot]:
        result = await self._session.execute(
            select(EnergyBalanceSnapshotModel)
            .where(
                EnergyBalanceSnapshotModel.site_id == site_id,
                EnergyBalanceSnapshotModel.charger_id == charger_id,
            )
            .order_by(desc(EnergyBalanceSnapshotModel.recorded_at))
            .offset(offset)
            .limit(limit)
        )
        return [self._to_stored(row) for row in result.scalars().all()]

    def _to_stored(self, row: EnergyBalanceSnapshotModel) -> StoredEnergyBalanceSnapshot:
        return StoredEnergyBalanceSnapshot(
            id=row.id,
            site_id=row.site_id,
            charger_id=row.charger_id,
            recorded_at=row.recorded_at,
            status=row.status,
            flags=json.loads(row.flags_json or "[]"),
            payload=json.loads(row.snapshot_json or "{}"),
        )
