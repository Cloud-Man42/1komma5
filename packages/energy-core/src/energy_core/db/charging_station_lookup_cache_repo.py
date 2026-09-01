"""Geohash-keyed charging station lookup cache."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import ChargingStationLookupCacheModel
from energy_core.integrations.charging_stations.geohash import encode
from energy_core.integrations.charging_stations.models import ResolvedChargingLocation


class ChargingStationLookupCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def cache_key(self, *, latitude: float, longitude: float, radius_m: int) -> str:
        return f"{encode(latitude, longitude, 6)}:{radius_m}"

    async def get(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
    ) -> ResolvedChargingLocation | None:
        key = self.cache_key(latitude=latitude, longitude=longitude, radius_m=radius_m)
        row = await self._session.get(ChargingStationLookupCacheModel, key)
        if row is None:
            return None
        now = datetime.now(UTC)
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= now:
            return None
        resolved = ResolvedChargingLocation.from_cache_dict(row.resolved_json)
        return resolved

    async def put(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
        resolved: ResolvedChargingLocation,
        ttl_seconds: float,
    ) -> None:
        key = self.cache_key(latitude=latitude, longitude=longitude, radius_m=radius_m)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)
        row = await self._session.get(ChargingStationLookupCacheModel, key)
        payload = resolved.to_cache_dict()
        if row is None:
            self._session.add(
                ChargingStationLookupCacheModel(
                    geohash_key=key,
                    latitude_rounded=round(latitude, 4),
                    longitude_rounded=round(longitude, 4),
                    radius_m=radius_m,
                    resolved_json=payload,
                    expires_at=expires_at,
                )
            )
        else:
            row.latitude_rounded = round(latitude, 4)
            row.longitude_rounded = round(longitude, 4)
            row.radius_m = radius_m
            row.resolved_json = payload
            row.expires_at = expires_at
        await self._session.flush()

    async def purge_expired(self) -> int:
        now = datetime.now(UTC)
        rows = await self._session.scalars(
            select(ChargingStationLookupCacheModel).where(
                ChargingStationLookupCacheModel.expires_at <= now
            )
        )
        count = 0
        for row in rows:
            await self._session.delete(row)
            count += 1
        if count:
            await self._session.flush()
        return count
