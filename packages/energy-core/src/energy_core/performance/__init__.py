"""Performance instrumentation for EMIC.

Backend-only modules (middleware, sql_tracking) are imported from their
submodules directly so the collector package does not require Starlette.
"""

from energy_core.performance.context import PerformanceContext, get_performance_context
from energy_core.performance.provider_metrics import ProviderMetrics, record_provider_call
from energy_core.performance.store import PerformanceStore, get_performance_store

__all__ = [
    "PerformanceContext",
    "PerformanceStore",
    "ProviderMetrics",
    "get_performance_context",
    "get_performance_store",
    "record_provider_call",
]
