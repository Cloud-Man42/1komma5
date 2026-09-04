"""Redis pub/sub for snapshot SSE push (Phase 8)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

from energy_core.config import Settings, get_settings

logger = logging.getLogger(__name__)

PUBSUB_POLL_TIMEOUT_SECONDS = 1.0


def snapshot_event_channel(site_id: int) -> str:
    return f"emic:events:snapshot:{site_id}"


class SnapshotEventPublisher:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url.strip()
        self._client: Any | None = None
        self._available = bool(self._redis_url)

    @property
    def configured(self) -> bool:
        return bool(self._redis_url)

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    async def _get_client(self) -> Any | None:
        if not self._available or not self._redis_url:
            return None
        if self._client is not None:
            return self._client
        try:
            from redis.asyncio import Redis

            client = Redis.from_url(self._redis_url, decode_responses=True)
            await client.ping()
            self._client = client
            return self._client
        except Exception:
            logger.warning("Snapshot pub/sub unavailable; SSE falls back to polling", exc_info=True)
            self._available = False
            self._client = None
            return None

    async def publish(self, site_id: int, payload: dict[str, Any]) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        message = json.dumps(
            {
                "type": "snapshot",
                "site_id": site_id,
                "generated_at": payload.get("generated_at"),
                "payload": payload,
            },
            default=str,
        )
        try:
            await client.publish(snapshot_event_channel(site_id), message)
            return True
        except Exception:
            logger.debug("Snapshot pub/sub publish failed for site %s", site_id, exc_info=True)
            return False


_publisher_singleton: SnapshotEventPublisher | None = None
_publisher_key: str | None = None


def get_snapshot_publisher(settings: Settings | None = None) -> SnapshotEventPublisher:
    global _publisher_singleton, _publisher_key
    settings = settings or get_settings()
    key = settings.redis_url or ""
    if _publisher_singleton is None or _publisher_key != key:
        _publisher_singleton = SnapshotEventPublisher(key)
        _publisher_key = key
    return _publisher_singleton


def reset_snapshot_publisher() -> None:
    global _publisher_singleton, _publisher_key
    _publisher_singleton = None
    _publisher_key = None


async def publish_snapshot_event(settings: Settings, site_id: int, payload: dict[str, Any]) -> bool:
    if not (settings.redis_url or "").strip():
        return False
    return await get_snapshot_publisher(settings).publish(site_id, payload)


async def snapshot_pubsub_available(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not (settings.redis_url or "").strip():
        return False
    publisher = get_snapshot_publisher(settings)
    await publisher._get_client()
    return publisher.available


async def snapshot_pubsub_status(settings: Settings | None = None) -> dict[str, bool]:
    settings = settings or get_settings()
    configured = bool((settings.redis_url or "").strip())
    if not configured:
        return {
            "snapshot_pubsub_configured": False,
            "snapshot_pubsub_available": False,
        }
    return {
        "snapshot_pubsub_configured": True,
        "snapshot_pubsub_available": await snapshot_pubsub_available(settings),
    }


async def listen_snapshot_events(
    settings: Settings,
    site_id: int,
) -> AsyncIterator[dict[str, Any]]:
    url = (settings.redis_url or "").strip()
    if not url:
        return
    client: Any | None = None
    pubsub: Any | None = None
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(url, decode_responses=True)
        await client.ping()
        pubsub = client.pubsub()
        await pubsub.subscribe(snapshot_event_channel(site_id))
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=PUBSUB_POLL_TIMEOUT_SECONDS,
            )
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                logger.debug("Ignoring malformed snapshot pub/sub payload")
                continue
            if isinstance(event, dict):
                yield event
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("Snapshot pub/sub listener stopped", exc_info=True)
    finally:
        if pubsub is not None:
            with suppress(Exception):
                await pubsub.unsubscribe(snapshot_event_channel(site_id))
                await pubsub.aclose()
        if client is not None:
            with suppress(Exception):
                await client.aclose()
