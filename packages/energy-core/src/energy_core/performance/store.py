"""In-memory performance metrics store for API and provider timings."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RequestMetric:
    request_id: str
    route: str
    total_ms: float
    db_ms: float
    cache_ms: float
    external_ms: float
    calculation_ms: float
    serialization_ms: float
    query_count: int
    response_bytes: int
    cache_hit: bool
    site_id: int | None
    timestamp: float


@dataclass(frozen=True, slots=True)
class SlowQueryMetric:
    sql: str
    duration_ms: float
    timestamp: float
    route: str = ""


class PerformanceStore:
    """Thread-safe rolling window of request and query metrics."""

    def __init__(self, max_requests: int = 5000, max_slow_queries: int = 500) -> None:
        self._lock = threading.Lock()
        self._requests: deque[RequestMetric] = deque(maxlen=max_requests)
        self._slow_queries: deque[SlowQueryMetric] = deque(maxlen=max_slow_queries)
        self._cache_hits = 0
        self._cache_misses = 0

    def record_request(self, metric: RequestMetric) -> None:
        with self._lock:
            self._requests.append(metric)
            if metric.cache_hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    def record_slow_query(self, metric: SlowQueryMetric) -> None:
        with self._lock:
            self._slow_queries.append(metric)

    def cache_stats(self) -> dict[str, int | float]:
        with self._lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total * 100.0) if total else 0.0
            return {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate_pct": round(hit_rate, 1),
            }

    def route_stats(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            by_route: dict[str, list[float]] = {}
            for m in self._requests:
                by_route.setdefault(m.route, []).append(m.total_ms)
        rows: list[dict[str, Any]] = []
        for route, times in by_route.items():
            times_sorted = sorted(times)
            n = len(times_sorted)
            p50 = times_sorted[n // 2]
            p95 = times_sorted[int(n * 0.95)] if n > 1 else times_sorted[0]
            rows.append({"route": route, "count": n, "p50_ms": round(p50, 1), "p95_ms": round(p95, 1)})
        rows.sort(key=lambda r: r["p95_ms"], reverse=True)
        return rows[:limit]

    def slowest_requests(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = sorted(self._requests, key=lambda m: m.total_ms, reverse=True)[:limit]
        return [
            {
                "request_id": m.request_id,
                "route": m.route,
                "total_ms": round(m.total_ms, 1),
                "db_ms": round(m.db_ms, 1),
                "external_ms": round(m.external_ms, 1),
                "query_count": m.query_count,
                "response_bytes": m.response_bytes,
                "cache_hit": m.cache_hit,
            }
            for m in items
        ]

    def slow_queries(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = sorted(self._slow_queries, key=lambda q: q.duration_ms, reverse=True)[:limit]
        return [
            {
                "sql": q.sql[:200],
                "duration_ms": round(q.duration_ms, 1),
                "route": q.route,
            }
            for q in items
        ]

    def summary(self) -> dict[str, Any]:
        with self._lock:
            count = len(self._requests)
        return {
            "request_count": count,
            "cache": self.cache_stats(),
            "slowest_routes": self.route_stats(10),
            "slowest_requests": self.slowest_requests(10),
            "slow_queries": self.slow_queries(10),
        }


_store = PerformanceStore()


def get_performance_store() -> PerformanceStore:
    return _store
