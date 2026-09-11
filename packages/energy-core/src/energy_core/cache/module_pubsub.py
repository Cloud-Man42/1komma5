"""Redis pub/sub for cross-process module enable/disable events."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

from energy_core.config import Settings, get_settings

logger = logging.getLogger(__name__)

MODULE_EVENTS_CHANNEL = "emic:events:modules"


class ModuleEventPublisher:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url.strip()
        self._client: Any | None = None
        self._available = bool(self._redis_url)

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
            logger.warning("Module pub/sub unavailable", exc_info=True)
            self._available = False
            self._client = None
            return None

    async def publish(self, site_id: int, module_id: str, enabled: bool) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        message = json.dumps({"site_id": site_id, "module_id": module_id, "enabled": enabled})
        try:
            await client.publish(MODULE_EVENTS_CHANNEL, message)
            return True
        except Exception:
            logger.debug("Module pub/sub publish failed site=%s module=%s", site_id, module_id, exc_info=True)
            return False

    async def publish_restart(self, site_id: int, module_id: str) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        message = json.dumps({"site_id": site_id, "module_id": module_id, "action": "restart"})
        try:
            await client.publish(MODULE_EVENTS_CHANNEL, message)
            return True
        except Exception:
            logger.debug("Module pub/sub restart failed site=%s module=%s", site_id, module_id, exc_info=True)
            return False


_publisher_singleton: ModuleEventPublisher | None = None
_publisher_key: str | None = None


def get_module_event_publisher(settings: Settings | None = None) -> ModuleEventPublisher:
    global _publisher_singleton, _publisher_key
    settings = settings or get_settings()
    key = settings.redis_url or ""
    if _publisher_singleton is None or _publisher_key != key:
        _publisher_singleton = ModuleEventPublisher(key)
        _publisher_key = key
    return _publisher_singleton


async def publish_module_state_change(
    settings: Settings,
    site_id: int,
    module_id: str,
    enabled: bool,
) -> bool:
    if not (settings.redis_url or "").strip():
        return False
    return await get_module_event_publisher(settings).publish(site_id, module_id, enabled)


async def publish_module_restart(
    settings: Settings,
    site_id: int,
    module_id: str,
) -> bool:
    if not (settings.redis_url or "").strip():
        return False
    return await get_module_event_publisher(settings).publish_restart(site_id, module_id)


async def listen_module_events(settings: Settings) -> AsyncIterator[dict[str, Any]]:
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
        await pubsub.subscribe(MODULE_EVENTS_CHANNEL)
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
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
                continue
            if isinstance(event, dict):
                yield event
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("Module pub/sub listener stopped", exc_info=True)
    finally:
        if pubsub is not None:
            with suppress(Exception):
                await pubsub.unsubscribe(MODULE_EVENTS_CHANNEL)
                await pubsub.aclose()
        if client is not None:
            with suppress(Exception):
                await client.aclose()
