"""Cached widget snapshot orchestration."""

from __future__ import annotations

from energy_core.config import Settings
from energy_core.db.models import SiteModel
from energy_core.energy_state.cache import SnapshotCache
from energy_core.energy_state.models import EnergySiteSnapshot
from energy_core.energy_state.service import EnergyStateService
from sqlalchemy.ext.asyncio import AsyncSession

_SNAPSHOT_CACHE = SnapshotCache[EnergySiteSnapshot](ttl_seconds=15.0)


def configure_snapshot_cache(settings: Settings) -> None:
    global _SNAPSHOT_CACHE
    _SNAPSHOT_CACHE = SnapshotCache[EnergySiteSnapshot](
        ttl_seconds=float(settings.widget_snapshot_cache_seconds)
    )


def clear_snapshot_cache() -> None:
    _SNAPSHOT_CACHE.clear()


class WidgetSnapshotService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._energy = EnergyStateService(session, settings)

    async def get_snapshot(self, site: SiteModel) -> EnergySiteSnapshot:
        cached = _SNAPSHOT_CACHE.get(site.slug)
        if cached is not None:
            return cached
        snapshot = await self._energy.build_snapshot(site)
        _SNAPSHOT_CACHE.set(site.slug, snapshot)
        return snapshot
