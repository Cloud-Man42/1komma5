"""Request-scoped performance context."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceContext:
    request_id: str = ""
    route: str = ""
    site_id: int | None = None
    db_ms: float = 0.0
    cache_ms: float = 0.0
    external_ms: float = 0.0
    calculation_ms: float = 0.0
    serialization_ms: float = 0.0
    query_count: int = 0
    cache_hit: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def add_db_ms(self, ms: float) -> None:
        self.db_ms += ms
        self.query_count += 1

    def add_external_ms(self, ms: float) -> None:
        self.external_ms += ms

    def add_cache_ms(self, ms: float) -> None:
        self.cache_ms += ms

    def add_calculation_ms(self, ms: float) -> None:
        self.calculation_ms += ms

    def add_serialization_ms(self, ms: float) -> None:
        self.serialization_ms += ms


_perf_ctx: ContextVar[PerformanceContext | None] = ContextVar("emic_perf_ctx", default=None)


def get_performance_context() -> PerformanceContext | None:
    return _perf_ctx.get()


def set_performance_context(ctx: PerformanceContext) -> None:
    _perf_ctx.set(ctx)


def clear_performance_context() -> None:
    _perf_ctx.set(None)
