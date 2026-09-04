# Observability — Collector Tasks & Request Correlation

**Status:** Implemented  
**Migration:** `060_collector_tasks_integration_health` (`collector_task_runs` table)

---

## Collector task runs

### Table: `collector_task_runs`

| Column | Type |
|--------|------|
| `id` | serial PK |
| `task_name` | varchar(64) — e.g. `snapshot_write`, `financial_rollup:akarp` |
| `lane` | varchar(16) — `fast`, `medium`, `slow` |
| `started_at` | timestamptz |
| `duration_ms` | float |
| `success` | boolean |
| `error_class` | varchar(128), nullable |

Indexes: `started_at`, `lane`.

### Recording

**File:** [`performance/task_metrics.py`](../../../packages/energy-core/src/energy_core/performance/task_metrics.py)

- `record_collector_task()` — called from `Collector._run_lane()` ([`collector.py`](../../../collector/app/collector.py))
- Auto-prunes rows older than **48 h**
- Failures logged at DEBUG if DB write fails (non-blocking)

### Query API

**Route:** `GET /api/system/performance` — [`backend/app/api/system.py`](../../../backend/app/api/system.py)

Response includes `tasks` object from `summarize_collector_tasks()`:

```json
{
  "tasks": {
    "lanes": {
      "fast": {"count": 120, "p50_ms": 450.2, "p95_ms": 890.1},
      "medium": {"count": 24, "p50_ms": 1200.0, "p95_ms": 3500.0},
      "slow": {"count": 8, "p50_ms": 8000.0, "p95_ms": 15000.0}
    },
    "failures": 2,
    "sample_size": 152
  }
}
```

Baseline collector cycle duration was **UNMEASURED** pre-Phase-1 ([`01_BASELINE.md`](01_BASELINE.md)); post-deploy values go in [`14_RESULTS.md`](14_RESULTS.md).

---

## HTTP request correlation

**File:** [`performance/middleware.py`](../../../packages/energy-core/src/energy_core/performance/middleware.py)

| Feature | Behaviour |
|---------|-----------|
| Request ID | `X-Request-Id` header or generated UUID (12 chars) |
| Context | `PerformanceContext` with route, timings, query count |
| Response header | `X-Request-Id` echoed |
| Logging | [`logging_context.py`](../../../packages/energy-core/src/energy_core/performance/logging_context.py) — `request_id_var` injected into log records as `record.request_id` |

Slow request logging includes request_id for cross-service tracing.

---

## Frontend

Performance center page polls `/api/system/performance` every 10 s — [`frontend/src/app/sites/[slug]/system/performance/page.tsx`](../../../frontend/src/app/sites/[slug]/system/performance/page.tsx).

Task lane stats can be added to UI in Phase 2 (API field already present).

---

## Tests

[`packages/energy-core/tests/performance/test_instrumentation.py`](../../../packages/energy-core/tests/performance/test_instrumentation.py) — performance context, middleware request ID.

[`backend/tests/test_system_api.py`](../../../backend/tests/test_system_api.py) — performance endpoint shape.
