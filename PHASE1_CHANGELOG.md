# EMIC Phase 1 Changelog

**Date:** 2026-09-03  
**Baseline:** [`docs/emic-analysis/phase1/01_BASELINE.md`](docs/emic-analysis/phase1/01_BASELINE.md)  
**Plan:** [`docs/emic-analysis/phase1/00_PLAN.md`](docs/emic-analysis/phase1/00_PLAN.md)

---

## 1. UnifiedEnergyState

### WHAT
Canonical runtime energy model with section dataclasses and adapters from `EnergyState`, `EnergySiteSnapshot`, and site live snapshot JSON.

### WHY
Single source of truth for Phase 2 optimizers (battery, horizon) without duplicating W/kW conversions and freshness logic.

### FILES
- `packages/energy-core/src/energy_core/energy/unified.py`
- `packages/energy-core/src/energy_core/energy/unified_adapters.py`
- `packages/energy-core/src/energy_core/optimization/context.py`
- `packages/energy-core/tests/energy/test_unified_state.py`

### MIGRATION
None.

### RISK
Low — additive; no API shape changes.

### TESTS
`test_unified_state.py` — adapters, conversion, freshness.

### PERFORMANCE BEFORE
N/A (not on hot path).

### PERFORMANCE AFTER
N/A.

### ROLLBACK
Remove module; no DB impact.

---

## 2. Solar Forecast API Snapshot

### WHAT
Pre-serialised solar forecast JSON in `solar_forecast_api_snapshots`; read-first API path; sync refresh on read disabled by default.

### WHY
Baseline solar forecast p95 **262 ms** (target < 100 ms). Eliminate synchronous coordinator refresh on GET.

### FILES
- `alembic/versions/058_solar_forecast_api_snapshots.py`
- `packages/energy-core/src/energy_core/db/solar_api_snapshot_repo.py`
- `packages/energy-core/src/energy_core/solar_forecast/api_read.py`
- `packages/energy-core/src/energy_core/solar_forecast/api_snapshot_builder.py`
- `packages/energy-core/src/energy_core/snapshots/writer.py`
- `backend/app/api/solar_forecast.py`
- `backend/tests/test_solar_forecast_snapshot_api.py`

### MIGRATION
`alembic upgrade head` (revision `058`).

### RISK
Sites without collector cycle serve fallback path or 503 until first snapshot write. Stale snapshot served when forecast refresh delayed.

### TESTS
`test_solar_forecast_snapshot_api.py`.

### PERFORMANCE BEFORE
`/solar/forecast` p95 **261.6 ms** (1 user).

### PERFORMANCE AFTER
_Pending deploy re-benchmark._

### ROLLBACK
Drop table `058` downgrade; set `SOLAR_FORECAST_SYNC_REFRESH_ON_READ=true` for legacy behaviour.

---

## 3. Financial Daily Aggregates

### WHAT
`financial_daily` table, shared `aggregation.py`, collector slow-lane rollup, flag-gated fast read in financial-stats API.

### WHY
Baseline financial-stats p95 **~3089 ms** (1 user), **~28 s** (10 users). Target < 300 ms.

### FILES
- `alembic/versions/059_financial_daily.py`
- `packages/energy-core/src/energy_core/financial/aggregation.py`
- `packages/energy-core/src/energy_core/financial/service.py`
- `packages/energy-core/src/energy_core/financial/daily_repo.py`
- `packages/energy-core/src/energy_core/db/repositories.py` (`list_financial_stats` aggregate path)
- `backend/app/api/readings.py`
- `collector/app/collector.py` (slow lane)
- `scripts/backfill_financial_daily.py`
- `packages/energy-core/tests/financial/test_aggregation_parity.py`

### MIGRATION
Revision `059`. Backfill: `python scripts/backfill_financial_daily.py --site akarp --days 365`.

### RISK
Flag off by default — no perf gain until enabled. Aggregate/read mismatch if backfill incomplete (mitigated by parity tests). Tax credit yearly allocation still computed at read time.

### TESTS
`test_aggregation_parity.py`.

### PERFORMANCE BEFORE
financial-stats p95 **3089 ms** (day/month/year, 1 user).

### PERFORMANCE AFTER
_Pending: enable `FINANCIAL_AGGREGATES_ENABLED=true` + re-benchmark._

### ROLLBACK
Set `FINANCIAL_AGGREGATES_ENABLED=false`; API uses full scan. Drop table via `059` downgrade.

---

## 4. Collector Fast / Medium / Slow Lanes

### WHAT
Three independent asyncio loops with configurable intervals; per-task metrics; `SitePollContext` for shared live overview prefetch.

### WHY
Isolate slow work (solar, financial rollup) from 30 s heartbeat path; observability per task.

### FILES
- `collector/app/collector.py`
- `collector/app/site_poll_context.py`
- `collector/tests/test_collector_lanes.py`
- `packages/energy-core/src/energy_core/config.py` (lane intervals)

### MIGRATION
None.

### RISK
Medium lane failure does not block fast lane. Slow lane lag up to 15 min for financial rollup. Lane timeout (120 s) may abort long tasks.

### TESTS
`test_collector_lanes.py`.

### PERFORMANCE BEFORE
Collector cycle duration UNMEASURED.

### PERFORMANCE AFTER
_Pending: `/api/system/performance` → `tasks.lanes`._

### ROLLBACK
Revert to single `poll_once()` loop (git revert collector changes).

---

## 5. Integration Health

### WHAT
`integration_health` table, recorder on Heartbeat prefetch, `GET /api/sites/{slug}/integration-health`.

### WHY
Surface provider staleness and failure counts for diagnostics and future alerting.

### FILES
- `alembic/versions/060_collector_tasks_integration_health.py` (partial)
- `packages/energy-core/src/energy_core/integrations/health.py`
- `backend/app/api/integration_health.py`
- `backend/app/main.py`
- `collector/app/collector.py` (`_prefetch_live_overviews`)

### MIGRATION
Revision `060`.

### RISK
Only `heartbeat` provider recorded initially. Stale threshold (300 s) may mark ok providers stale on slow poll intervals.

### TESTS
`test_integration_health_api.py`.

### PERFORMANCE BEFORE
N/A.

### PERFORMANCE AFTER
N/A.

### ROLLBACK
`060` downgrade drops `integration_health` table.

---

## 6. Collector Task Observability

### WHAT
`collector_task_runs` table; `summarize_collector_tasks()` exposed in `/api/system/performance`.

### WHY
Baseline had no collector instrumentation; needed for Phase 1 results and ops debugging.

### FILES
- `alembic/versions/060_collector_tasks_integration_health.py`
- `packages/energy-core/src/energy_core/performance/task_metrics.py`
- `backend/app/api/system.py`
- `collector/app/collector.py` (`_run_lane`)

### MIGRATION
Revision `060`.

### RISK
48 h auto-retention; high-volume task names (`financial_rollup:*`) — pruned automatically. Write failures are non-blocking.

### TESTS
`test_instrumentation.py`, `test_system_api.py`.

### PERFORMANCE BEFORE
UNMEASURED.

### PERFORMANCE AFTER
_Pending._

### ROLLBACK
`060` downgrade; remove `record_collector_task` calls.

---

## 7. Request Correlation ID

### WHAT
`X-Request-Id` on all API responses; context var for structured logging.

### WHY
Trace slow requests across logs and performance store.

### FILES
- `packages/energy-core/src/energy_core/performance/middleware.py`
- `packages/energy-core/src/energy_core/performance/logging_context.py`

### MIGRATION
None.

### RISK
Low.

### TESTS
`test_instrumentation.py`.

### PERFORMANCE BEFORE
N/A.

### PERFORMANCE AFTER
N/A.

### ROLLBACK
Remove middleware registration in `backend/app/main.py`.

---

## 8. Pi LKG localStorage

### WHAT
Last-known-good display overview in localStorage; connection states; exponential backoff on poll failure.

### WHY
Pi kiosk resilience during brief network outages; show lastUpdated timestamp.

### FILES
- `frontend/src/lib/piDashboardStorage.ts`
- `frontend/src/lib/usePiDashboardData.ts`
- `frontend/src/lib/piDashboardStorage.test.ts`

### MIGRATION
None.

### RISK
Stale data shown as `STALE` up to 900 s. localStorage cleared on browser data wipe.

### TESTS
`piDashboardStorage.test.ts`.

### PERFORMANCE BEFORE
Pi display UNMEASURED.

### PERFORMANCE AFTER
_Pending._

### ROLLBACK
Revert hook to poll-only without LKG.

---

## 9. Config Defaults (breaking behaviour change)

### WHAT
`solar_forecast_sync_refresh_on_read` default **`false`**.

### WHY
Prevent read-path blocking on external weather/coordinator calls.

### FILES
- `packages/energy-core/src/energy_core/config.py`

### MIGRATION
None — env override `SOLAR_FORECAST_SYNC_REFRESH_ON_READ=true` restores old behaviour.

### RISK
Stale forecast served until collector refreshes. Document in ops runbook.

### TESTS
Covered in `test_solar_forecast_snapshot_api.py`.

### PERFORMANCE BEFORE
262 ms p95 with occasional multi-second spikes on stale refresh.

### PERFORMANCE AFTER
_Pending._

### ROLLBACK
Set env `SOLAR_FORECAST_SYNC_REFRESH_ON_READ=true`.

---

## 10. Design Only (no code)

| Topic | Doc |
|-------|-----|
| Redis cache | [`docs/emic-analysis/phase1/06_CACHE.md`](docs/emic-analysis/phase1/06_CACHE.md) |
| SSE pub/sub | [`docs/emic-analysis/phase1/07_REALTIME.md`](docs/emic-analysis/phase1/07_REALTIME.md) |
| Auth plan + P0 `/apple-devices` | [`docs/emic-analysis/phase1/10_SECURITY.md`](docs/emic-analysis/phase1/10_SECURITY.md) |
| DB retention script | [`scripts/retention-policies.sql`](scripts/retention-policies.sql) |

---

## Deploy checklist

1. `alembic upgrade head` (058 → 060)
2. Deploy backend + collector + frontend
3. `python scripts/backfill_financial_daily.py --site akarp --days 365`
4. Set `FINANCIAL_AGGREGATES_ENABLED=true` when ready
5. Confirm `SOLAR_FORECAST_SYNC_REFRESH_ON_READ=false`
6. Run `scripts/phase1-baseline.ps1` → update [`14_RESULTS.md`](docs/emic-analysis/phase1/14_RESULTS.md)
