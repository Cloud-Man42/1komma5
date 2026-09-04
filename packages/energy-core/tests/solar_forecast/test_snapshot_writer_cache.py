"""Snapshot writer cache write-through tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.config import Settings
from energy_core.snapshots.writer import SnapshotWriter


@pytest.mark.asyncio
async def test_snapshot_writer_writes_through_to_cache() -> None:
    settings = Settings(_env_file=None, REDIS_URL="")
    writer = SnapshotWriter(settings)
    site = MagicMock(id=7, slug="akarp", timezone="Europe/Stockholm")
    payload = {"site": {"slug": "akarp"}, "generated_at": "2026-09-03T12:00:00Z"}

    session = AsyncMock()
    cache = AsyncMock()

    with (
        patch.object(writer, "_builder") as builder,
        patch("energy_core.snapshots.writer.SiteLiveSnapshotRepository") as repo_cls,
        patch("energy_core.snapshots.writer.SolarForecastApiSnapshotRepository"),
        patch("energy_core.snapshots.writer.SolarForecastRepository"),
        patch("energy_core.snapshots.writer.SolarSiteConfigRepository") as config_repo_cls,
        patch("energy_core.cache.service.get_cache_service", return_value=cache),
        patch("energy_core.cache.service.site_snapshot_cache_key", return_value="emic:site:7:snapshot"),
    ):
        builder.build = AsyncMock(return_value=payload)
        repo = repo_cls.return_value
        repo.upsert = AsyncMock()
        config_repo = config_repo_cls.return_value
        config_repo.get = AsyncMock(return_value=None)

        count = await writer.write_all_sites(session, [site])

    assert count == 1
    cache.set.assert_awaited_once_with(
        "emic:site:7:snapshot",
        payload,
        ttl_seconds=settings.snapshot_redis_cache_ttl_seconds,
    )


@pytest.mark.asyncio
async def test_snapshot_writer_publishes_sse_event() -> None:
    settings = Settings(_env_file=None, REDIS_URL="redis://127.0.0.1:6379/0")
    writer = SnapshotWriter(settings)
    site = MagicMock(id=7, slug="akarp", timezone="Europe/Stockholm")
    payload = {"site": {"slug": "akarp"}, "generated_at": "2026-09-03T12:00:00Z"}

    session = AsyncMock()
    cache = AsyncMock()
    publish = AsyncMock(return_value=True)

    with (
        patch.object(writer, "_builder") as builder,
        patch("energy_core.snapshots.writer.SiteLiveSnapshotRepository") as repo_cls,
        patch("energy_core.snapshots.writer.SolarForecastApiSnapshotRepository"),
        patch("energy_core.snapshots.writer.SolarForecastRepository"),
        patch("energy_core.snapshots.writer.SolarSiteConfigRepository") as config_repo_cls,
        patch("energy_core.cache.service.get_cache_service", return_value=cache),
        patch("energy_core.cache.service.site_snapshot_cache_key", return_value="emic:site:7:snapshot"),
        patch("energy_core.cache.snapshot_pubsub.publish_snapshot_event", publish),
    ):
        builder.build = AsyncMock(return_value=payload)
        repo = repo_cls.return_value
        repo.upsert = AsyncMock()
        config_repo = config_repo_cls.return_value
        config_repo.get = AsyncMock(return_value=None)

        await writer.write_all_sites(session, [site])

    publish.assert_awaited_once_with(settings, 7, payload)
