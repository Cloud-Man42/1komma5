"""Optional Redis L2 cache with graceful degradation."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisCacheService:
    """Redis-backed cache; silently degrades when Redis is unavailable."""

    def __init__(self, redis_url: str, *, default_ttl_seconds: float = 60.0) -> None:
        self._redis_url = redis_url.strip()
        self._default_ttl_seconds = default_ttl_seconds
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
            logger.warning("Redis cache unavailable; falling back to in-memory only", exc_info=True)
            self._available = False
            self._client = None
            return None

    async def get(self, key: str) -> Any | None:
        client = await self._get_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.debug("Redis cache get failed for %s", key, exc_info=True)
            return None

    async def set(self, key: str, value: Any, *, ttl_seconds: float) -> None:
        client = await self._get_client()
        if client is None:
            return
        ttl = max(int(ttl_seconds or self._default_ttl_seconds), 1)
        try:
            await client.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception:
            logger.debug("Redis cache set failed for %s", key, exc_info=True)

    async def invalidate(self, key: str) -> None:
        client = await self._get_client()
        if client is None:
            return
        try:
            await client.delete(key)
        except Exception:
            logger.debug("Redis cache invalidate failed for %s", key, exc_info=True)
