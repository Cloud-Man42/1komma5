"""External provider call metrics."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from energy_core.performance.context import get_performance_context


@dataclass(frozen=True, slots=True)
class ProviderMetrics:
    provider: str
    latency_ms: float
    success: bool
    site_id: int | None = None
    timestamp: float = 0.0


class ProviderMetricsStore:
    def __init__(self, max_entries: int = 2000) -> None:
        self._lock = threading.Lock()
        self._entries: deque[ProviderMetrics] = deque(maxlen=max_entries)

    def record(self, metric: ProviderMetrics) -> None:
        with self._lock:
            self._entries.append(metric)

    def summary(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            by_provider: dict[str, list[float]] = {}
            errors: dict[str, int] = {}
            for e in self._entries:
                by_provider.setdefault(e.provider, []).append(e.latency_ms)
                if not e.success:
                    errors[e.provider] = errors.get(e.provider, 0) + 1
        rows: list[dict[str, Any]] = []
        for provider, latencies in by_provider.items():
            latencies.sort()
            n = len(latencies)
            avg = sum(latencies) / n
            rows.append(
                {
                    "provider": provider,
                    "calls": n,
                    "avg_ms": round(avg, 1),
                    "errors": errors.get(provider, 0),
                }
            )
        rows.sort(key=lambda r: r["avg_ms"], reverse=True)
        return rows[:limit]


_provider_store = ProviderMetricsStore()


def get_provider_metrics_store() -> ProviderMetricsStore:
    return _provider_store


def record_provider_call(
    provider: str,
    latency_ms: float,
    *,
    success: bool = True,
    site_id: int | None = None,
) -> None:
    ctx = get_performance_context()
    if ctx is not None:
        ctx.add_external_ms(latency_ms)
    _provider_store.record(
        ProviderMetrics(
            provider=provider,
            latency_ms=latency_ms,
            success=success,
            site_id=site_id,
            timestamp=time.time(),
        )
    )
