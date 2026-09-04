"""Snapshot Redis pub/sub tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from energy_core.cache.snapshot_pubsub import (
    SnapshotEventPublisher,
    get_snapshot_publisher,
    publish_snapshot_event,
    reset_snapshot_publisher,
    snapshot_event_channel,
    snapshot_pubsub_available,
)
from energy_core.config import Settings


def test_snapshot_event_channel() -> None:
    assert snapshot_event_channel(7) == "emic:events:snapshot:7"


@pytest.mark.asyncio
async def test_publish_without_redis_url_is_noop() -> None:
    settings = Settings(_env_file=None, REDIS_URL="")
    payload = {"generated_at": "2026-09-03T12:00:00Z"}
    assert await publish_snapshot_event(settings, 1, payload) is False


@pytest.mark.asyncio
async def test_publisher_publishes_json_payload() -> None:
    reset_snapshot_publisher()
    publisher = SnapshotEventPublisher("redis://127.0.0.1:6379/0")
    fake_client = AsyncMock()
    fake_client.ping = AsyncMock()
    fake_client.publish = AsyncMock(return_value=1)

    with patch.object(publisher, "_get_client", AsyncMock(return_value=fake_client)):
        payload = {"generated_at": "2026-09-03T12:00:00Z", "site": {"slug": "akarp"}}
        ok = await publisher.publish(3, payload)

    assert ok is True
    fake_client.publish.assert_awaited_once()
    channel, message = fake_client.publish.await_args.args
    assert channel == "emic:events:snapshot:3"
    body = json.loads(message)
    assert body["type"] == "snapshot"
    assert body["site_id"] == 3
    assert body["payload"]["site"]["slug"] == "akarp"


@pytest.mark.asyncio
async def test_snapshot_pubsub_available_false_without_redis() -> None:
    reset_snapshot_publisher()
    settings = Settings(_env_file=None, REDIS_URL="")
    assert await snapshot_pubsub_available(settings) is False


@pytest.mark.asyncio
async def test_get_snapshot_publisher_singleton() -> None:
    reset_snapshot_publisher()
    settings = Settings(_env_file=None, REDIS_URL="redis://127.0.0.1:6379/0")
    first = get_snapshot_publisher(settings)
    second = get_snapshot_publisher(settings)
    assert first is second
