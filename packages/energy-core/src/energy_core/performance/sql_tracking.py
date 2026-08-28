"""SQLAlchemy query timing hooks."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from energy_core.performance.context import get_performance_context
from energy_core.performance.store import SlowQueryMetric, get_performance_store

logger = logging.getLogger(__name__)

SLOW_QUERY_MS = 100.0
_installed: set[int] = set()


def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    conn.info.setdefault("emic_query_start", []).append(time.perf_counter())


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    starts = conn.info.get("emic_query_start")
    if not starts:
        return
    start = starts.pop()
    duration_ms = (time.perf_counter() - start) * 1000.0
    perf = get_performance_context()
    if perf is not None:
        perf.add_db_ms(duration_ms)
    if duration_ms >= SLOW_QUERY_MS:
        route = perf.route if perf else ""
        sql = " ".join(statement.split())[:500]
        get_performance_store().record_slow_query(
            SlowQueryMetric(sql=sql, duration_ms=duration_ms, timestamp=time.time(), route=route)
        )
        logger.warning("slow query %.1fms route=%s sql=%s", duration_ms, route, sql[:120])


def install_sql_tracking(engine: Engine | AsyncEngine) -> None:
    sync_engine = engine.sync_engine if isinstance(engine, AsyncEngine) else engine
    key = id(sync_engine)
    if key in _installed:
        return
    event.listen(sync_engine, "before_cursor_execute", _before_cursor_execute)
    event.listen(sync_engine, "after_cursor_execute", _after_cursor_execute)
    _installed.add(key)
