"""Collector task metrics persistence and query."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.db.models import CollectorTaskRunModel
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MAX_ROWS = 5000
_RETENTION_HOURS = 48


async def record_collector_task(
    session_factory,
    *,
    task_name: str,
    lane: str,
    duration_ms: float,
    success: bool,
    error_class: str | None = None,
) -> None:
    try:
        async with session_factory() as session:
            session.add(
                CollectorTaskRunModel(
                    task_name=task_name,
                    lane=lane,
                    started_at=datetime.now(UTC),
                    duration_ms=round(duration_ms, 2),
                    success=success,
                    error_class=error_class,
                )
            )
            cutoff = datetime.now(UTC) - timedelta(hours=_RETENTION_HOURS)
            await session.execute(delete(CollectorTaskRunModel).where(CollectorTaskRunModel.started_at < cutoff))
            await session.commit()
    except Exception:
        logger.debug("Failed to record collector task %s", task_name, exc_info=True)


async def list_recent_collector_tasks(session: AsyncSession, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        await session.scalars(
            select(CollectorTaskRunModel).order_by(desc(CollectorTaskRunModel.started_at)).limit(limit)
        )
    ).all()
    return [
        {
            "task_name": row.task_name,
            "lane": row.lane,
            "started_at": row.started_at.astimezone(UTC).isoformat(),
            "duration_ms": row.duration_ms,
            "success": row.success,
            "error_class": row.error_class,
        }
        for row in rows
    ]


async def summarize_collector_tasks(session: AsyncSession) -> dict[str, Any]:
    rows = (
        await session.scalars(
            select(CollectorTaskRunModel).order_by(desc(CollectorTaskRunModel.started_at)).limit(_MAX_ROWS)
        )
    ).all()
    by_lane: dict[str, list[float]] = {}
    failures = 0
    for row in rows:
        by_lane.setdefault(row.lane, []).append(row.duration_ms)
        if not row.success:
            failures += 1
    lane_stats = {}
    for lane, durations in by_lane.items():
        sorted_d = sorted(durations)
        p95_idx = max(0, int(len(sorted_d) * 0.95) - 1)
        lane_stats[lane] = {
            "count": len(sorted_d),
            "p50_ms": round(sorted_d[len(sorted_d) // 2], 1) if sorted_d else 0,
            "p95_ms": round(sorted_d[p95_idx], 1) if sorted_d else 0,
        }
    return {"lanes": lane_stats, "failures": failures, "sample_size": len(rows)}
