"""Repository for Mercedes attribute observation persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleAttributeObservationModel
from energy_core.vehicles.mercedes.mapping.observer import AttributeObservation


@dataclass(frozen=True, slots=True)
class AttributeObservationRecord:
    attribute_name: str
    source: str
    value_type: str
    masked_sample: str
    first_seen_at: datetime
    last_seen_at: datetime
    sample_count: int


class VehicleAttributeObservationRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool = False) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def record_observations(
        self,
        vehicle_id: int,
        observations: list[AttributeObservation],
    ) -> None:
        if not observations:
            return
        now = datetime.now(UTC)
        insert = sqlite_insert if self._is_sqlite else pg_insert
        for obs in observations:
            values = {
                "vehicle_id": vehicle_id,
                "attribute_name": obs.attribute_name,
                "source": obs.source,
                "value_type": obs.value_type,
                "masked_sample": obs.masked_sample[:256],
                "first_seen_at": now,
                "last_seen_at": now,
                "sample_count": 1,
            }
            stmt = insert(VehicleAttributeObservationModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["vehicle_id", "attribute_name", "source"],
                set_={
                    "value_type": obs.value_type,
                    "masked_sample": obs.masked_sample[:256],
                    "last_seen_at": now,
                    "sample_count": VehicleAttributeObservationModel.sample_count + 1,
                },
            )
            await self._session.execute(stmt)

    async def list_for_vehicle(self, vehicle_id: int) -> list[AttributeObservationRecord]:
        result = await self._session.execute(
            select(VehicleAttributeObservationModel)
            .where(VehicleAttributeObservationModel.vehicle_id == vehicle_id)
            .order_by(VehicleAttributeObservationModel.attribute_name)
        )
        return [
            AttributeObservationRecord(
                attribute_name=row.attribute_name,
                source=row.source,
                value_type=row.value_type,
                masked_sample=row.masked_sample,
                first_seen_at=row.first_seen_at,
                last_seen_at=row.last_seen_at,
                sample_count=row.sample_count,
            )
            for row in result.scalars().all()
        ]

    async def list_for_site(self, site_id: int) -> list[tuple[int, AttributeObservationRecord]]:
        from energy_core.db.models import VehicleModel

        result = await self._session.execute(
            select(VehicleModel.id, VehicleAttributeObservationModel)
            .join(
                VehicleAttributeObservationModel,
                VehicleAttributeObservationModel.vehicle_id == VehicleModel.id,
            )
            .where(VehicleModel.site_id == site_id)
            .order_by(VehicleAttributeObservationModel.attribute_name)
        )
        rows: list[tuple[int, AttributeObservationRecord]] = []
        for vehicle_id, row in result.all():
            rows.append(
                (
                    vehicle_id,
                    AttributeObservationRecord(
                        attribute_name=row.attribute_name,
                        source=row.source,
                        value_type=row.value_type,
                        masked_sample=row.masked_sample,
                        first_seen_at=row.first_seen_at,
                        last_seen_at=row.last_seen_at,
                        sample_count=row.sample_count,
                    ),
                )
            )
        return rows
