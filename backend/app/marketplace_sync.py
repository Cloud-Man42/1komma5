"""Background marketplace metadata sync loop."""

from __future__ import annotations

import asyncio
import logging
import random

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_core.config import Settings
from energy_core.platform.modules.marketplace.sync_service import (
    MarketplaceSyncService,
    marketplace_sync_interval_seconds,
)

logger = logging.getLogger(__name__)


async def marketplace_metadata_sync_loop(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    stop_event: asyncio.Event,
) -> None:
    """Periodic metadata sync with backoff on failure."""
    failure_streak = 0
    while not stop_event.is_set():
        interval = marketplace_sync_interval_seconds(settings)
        if settings.marketplace_metadata_enabled:
            try:
                service = MarketplaceSyncService(settings)
                result = await service.sync_with_session_factory(session_factory)
                if result.outcome.value in {"success", "skipped"}:
                    failure_streak = 0
                else:
                    failure_streak += 1
                    logger.warning("Marketplace metadata sync failed: %s", result.message)
            except Exception:
                failure_streak += 1
                logger.exception("Marketplace metadata sync loop error")

        delay = interval
        if failure_streak:
            delay = min(interval * (2 ** min(failure_streak, 4)), interval * 8)
            delay += random.uniform(0, min(30.0, delay * 0.1))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except TimeoutError:
            continue
