"""Charging station persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import ChargingStationModel
from energy_core.integrations.charging_stations.models import ChargingStationCandidate, StationProvider


@dataclass(frozen=True, slots=True)
class ChargingStationRecord:
    id: int
    provider: str
    provider_station_id: str
    operator: str | None
    station_name: str | None
    latitude: float
    longitude: float
    user_confirmed: bool
    times_used: int


class ChargingStationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_from_candidate(self, candidate: ChargingStationCandidate) -> ChargingStationRecord:
        now = datetime.now(UTC)
        row = await self._session.scalar(
            select(ChargingStationModel).where(
                ChargingStationModel.provider == candidate.provider.value,
                ChargingStationModel.provider_station_id == candidate.provider_station_id,
            )
        )
        if row is None:
            row = ChargingStationModel(
                provider=candidate.provider.value,
                provider_station_id=candidate.provider_station_id,
                operator=candidate.operator,
                station_name=candidate.station_name,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                address=candidate.address,
                postal_code=candidate.postal_code,
                city=candidate.city,
                country=candidate.country,
                connector_type=candidate.connector_type,
                max_power_kw=candidate.max_power_kw,
                charging_type=candidate.charging_type,
                external_station_url=candidate.external_url,
                network_name=candidate.network_name,
                first_seen_at=now,
                last_seen_at=now,
                times_used=0,
                user_confirmed=False,
                raw_provider_data=candidate.raw_provider_data,
            )
            self._session.add(row)
        else:
            row.operator = candidate.operator or row.operator
            row.station_name = candidate.station_name or row.station_name
            row.latitude = candidate.latitude
            row.longitude = candidate.longitude
            row.address = candidate.address or row.address
            row.connector_type = candidate.connector_type or row.connector_type
            row.max_power_kw = candidate.max_power_kw or row.max_power_kw
            row.charging_type = candidate.charging_type or row.charging_type
            row.external_station_url = candidate.external_url or row.external_station_url
            row.network_name = candidate.network_name or row.network_name
            row.last_seen_at = now
            if candidate.raw_provider_data:
                row.raw_provider_data = candidate.raw_provider_data
        await self._session.flush()
        return _to_record(row)

    async def find_confirmed_near(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: float,
    ) -> list[ChargingStationRecord]:
        from energy_core.vehicles.charging_intelligence.location import haversine_m

        rows = await self._session.scalars(
            select(ChargingStationModel).where(ChargingStationModel.user_confirmed.is_(True))
        )
        matches: list[tuple[float, ChargingStationRecord]] = []
        for row in rows:
            distance = haversine_m(latitude, longitude, row.latitude, row.longitude)
            if distance <= radius_m:
                matches.append((distance, _to_record(row)))
        matches.sort(key=lambda item: item[0])
        return [record for _, record in matches]

    async def confirm_station(
        self,
        *,
        provider: str,
        provider_station_id: str,
        operator: str | None,
        station_name: str | None,
        latitude: float,
        longitude: float,
        connector_type: str | None = None,
        max_power_kw: float | None = None,
        charging_type: str | None = None,
    ) -> ChargingStationRecord:
        now = datetime.now(UTC)
        row = await self._session.scalar(
            select(ChargingStationModel).where(
                ChargingStationModel.provider == provider,
                ChargingStationModel.provider_station_id == provider_station_id,
            )
        )
        if row is None:
            row = ChargingStationModel(
                provider=provider,
                provider_station_id=provider_station_id,
                operator=operator,
                station_name=station_name,
                latitude=latitude,
                longitude=longitude,
                connector_type=connector_type,
                max_power_kw=max_power_kw,
                charging_type=charging_type,
                first_seen_at=now,
                last_seen_at=now,
                times_used=0,
                user_confirmed=True,
            )
            self._session.add(row)
        else:
            row.user_confirmed = True
            row.operator = operator or row.operator
            row.station_name = station_name or row.station_name
            row.latitude = latitude
            row.longitude = longitude
            row.last_seen_at = now
        await self._session.flush()
        return _to_record(row)

    async def record_usage(self, station_id: int) -> None:
        row = await self._session.get(ChargingStationModel, station_id)
        if row is None:
            return
        row.times_used += 1
        row.last_seen_at = datetime.now(UTC)
        await self._session.flush()

    async def get(self, station_id: int) -> ChargingStationRecord | None:
        row = await self._session.get(ChargingStationModel, station_id)
        return _to_record(row) if row else None


def _to_record(row: ChargingStationModel) -> ChargingStationRecord:
    return ChargingStationRecord(
        id=row.id,
        provider=row.provider,
        provider_station_id=row.provider_station_id,
        operator=row.operator,
        station_name=row.station_name,
        latitude=row.latitude,
        longitude=row.longitude,
        user_confirmed=row.user_confirmed,
        times_used=row.times_used,
    )
