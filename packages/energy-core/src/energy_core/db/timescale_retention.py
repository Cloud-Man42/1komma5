"""TimescaleDB retention policy management (Phase 11)."""

from __future__ import annotations

import logging
from typing import Any

from energy_core.config import Settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

RETENTION_POLICIES: dict[str, str] = {
    "energy_readings": "90 days",
    "consumer_samples": "90 days",
    "vehicle_state_history": "180 days",
}

COMPRESSION_POLICIES: dict[str, dict[str, str]] = {
    "energy_readings": {
        "compress_after": "7 days",
        "segmentby": "site_id",
    },
    "consumer_samples": {
        "compress_after": "7 days",
        "segmentby": "consumer_id",
    },
    "vehicle_state_history": {
        "compress_after": "14 days",
        "segmentby": "vehicle_id",
    },
}


async def _retention_policy_exists(session: AsyncSession, hypertable: str) -> bool:
    result = await session.execute(
        text(
            """
            SELECT 1
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_retention'
              AND hypertable_name = :hypertable
            LIMIT 1
            """
        ),
        {"hypertable": hypertable},
    )
    return result.scalar_one_or_none() is not None


async def ensure_timescale_retention(session: AsyncSession, settings: Settings) -> dict[str, Any]:
    if not settings.timescale_retention_enabled:
        return {"status": "disabled"}
    if settings.is_sqlite or not settings.enable_timescaledb or not settings.is_postgresql:
        return {"status": "skipped", "reason": "not_timescale"}

    applied: dict[str, str] = {}
    for hypertable, interval in RETENTION_POLICIES.items():
        try:
            if await _retention_policy_exists(session, hypertable):
                applied[hypertable] = "exists"
                continue
            await session.execute(
                text(f"SELECT add_retention_policy(:hypertable, INTERVAL '{interval}')"),
                {"hypertable": hypertable},
            )
            applied[hypertable] = "created"
        except Exception:
            logger.exception("Failed to ensure retention policy for %s", hypertable)
            applied[hypertable] = "error"

    return {"status": "applied", "policies": applied}


async def _compression_enabled(session: AsyncSession, hypertable: str) -> bool:
    result = await session.execute(
        text(
            """
            SELECT compression_enabled
            FROM timescaledb_information.hypertables
            WHERE hypertable_name = :hypertable
            """
        ),
        {"hypertable": hypertable},
    )
    return bool(result.scalar_one_or_none())


async def _compression_policy_exists(session: AsyncSession, hypertable: str) -> bool:
    result = await session.execute(
        text(
            """
            SELECT 1
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_compression'
              AND hypertable_name = :hypertable
            LIMIT 1
            """
        ),
        {"hypertable": hypertable},
    )
    return result.scalar_one_or_none() is not None


async def ensure_timescale_compression(session: AsyncSession, settings: Settings) -> dict[str, Any]:
    if not settings.timescale_compression_enabled:
        return {"status": "disabled"}
    if settings.is_sqlite or not settings.enable_timescaledb or not settings.is_postgresql:
        return {"status": "skipped", "reason": "not_timescale"}

    applied: dict[str, str] = {}
    for hypertable, policy in COMPRESSION_POLICIES.items():
        segmentby = policy["segmentby"]
        compress_after = policy["compress_after"]
        try:
            if await _compression_enabled(session, hypertable):
                applied[f"{hypertable}:compression"] = "exists"
            else:
                await session.execute(
                    text(
                        f"ALTER TABLE {hypertable} SET "
                        f"(timescaledb.compress, timescaledb.compress_segmentby = '{segmentby}')"
                    ),
                )
                applied[f"{hypertable}:compression"] = "enabled"

            if await _compression_policy_exists(session, hypertable):
                applied[f"{hypertable}:policy"] = "exists"
            else:
                await session.execute(
                    text(f"SELECT add_compression_policy(:hypertable, INTERVAL '{compress_after}')"),
                    {"hypertable": hypertable},
                )
                applied[f"{hypertable}:policy"] = "created"
        except Exception:
            logger.exception("Failed to ensure compression policy for %s", hypertable)
            applied[hypertable] = "error"

    return {"status": "applied", "policies": applied}


async def inspect_timescale_policies(session: AsyncSession, settings: Settings) -> dict[str, Any]:
    if settings.is_sqlite or not settings.is_postgresql:
        return {
            "status": "skipped",
            "reason": "not_timescale",
            "retention_enabled": settings.timescale_retention_enabled,
            "compression_enabled": settings.timescale_compression_enabled,
        }
    if not settings.enable_timescaledb:
        return {
            "status": "skipped",
            "reason": "timescaledb_disabled",
            "retention_enabled": settings.timescale_retention_enabled,
            "compression_enabled": settings.timescale_compression_enabled,
        }

    retention: dict[str, str] = {}
    for hypertable in RETENTION_POLICIES:
        retention[hypertable] = "exists" if await _retention_policy_exists(session, hypertable) else "missing"

    compression: dict[str, dict[str, Any]] = {}
    for hypertable in COMPRESSION_POLICIES:
        compression[hypertable] = {
            "compression_enabled": await _compression_enabled(session, hypertable),
            "policy": "exists" if await _compression_policy_exists(session, hypertable) else "missing",
        }

    retention_ok = all(state == "exists" for state in retention.values())
    compression_ok = all(
        row["compression_enabled"] and row["policy"] == "exists" for row in compression.values()
    )
    return {
        "status": "ok" if retention_ok and compression_ok else "incomplete",
        "retention_enabled": settings.timescale_retention_enabled,
        "compression_enabled": settings.timescale_compression_enabled,
        "retention": retention,
        "compression": compression,
    }
