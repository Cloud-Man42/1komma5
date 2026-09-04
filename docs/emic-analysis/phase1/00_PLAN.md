# Phase 1 Plan — EMIC Performance & Foundation

**Date:** 2026-09-03  
**Baseline:** [`01_BASELINE.md`](01_BASELINE.md) (measured pre-implementation on production `akarp`)

---

## Goal

Improve read-path latency for hot API routes, establish shared domain models and collector structure, and add observability — without breaking existing behaviour. Defer Redis, SSE pub/sub redesign, and auth hardening to design docs only.

---

## Scope

### In scope (implemented)

| # | Topic | Doc |
|---|-------|-----|
| 1 | Baseline measurement | [`01_BASELINE.md`](01_BASELINE.md) |
| 2 | `UnifiedEnergyState` + adapters | [`02_UNIFIED_ENERGY_STATE.md`](02_UNIFIED_ENERGY_STATE.md) |
| 3 | Solar forecast API snapshots | [`03_SOLAR_FORECAST_SNAPSHOT.md`](03_SOLAR_FORECAST_SNAPSHOT.md) |
| 4 | Financial daily aggregates | [`04_FINANCIAL_AGGREGATION.md`](04_FINANCIAL_AGGREGATION.md) |
| 5 | Collector fast/medium/slow lanes | [`05_COLLECTOR_LANES.md`](05_COLLECTOR_LANES.md) |
| 8 | Pi LKG localStorage | [`08_PI.md`](08_PI.md) |
| 9 | Integration health API | [`09_INTEGRATION_HEALTH.md`](09_INTEGRATION_HEALTH.md) |
| 11 | Collector task metrics + correlation IDs | [`11_OBSERVABILITY.md`](11_OBSERVABILITY.md) |
| 12 | Retention recommendations | [`12_DATABASE_RETENTION.md`](12_DATABASE_RETENTION.md) |
| 13 | New tests | [`13_TESTS.md`](13_TESTS.md) |
| 14 | Before/after results | [`14_RESULTS.md`](14_RESULTS.md) |
| 15 | Remaining risks | [`15_REMAINING_RISKS.md`](15_REMAINING_RISKS.md) |
| 16 | Phase 2 recommendations | [`16_PHASE2_RECOMMENDATIONS.md`](16_PHASE2_RECOMMENDATIONS.md) |

### Design only (documented, not activated)

| # | Topic | Doc |
|---|-------|-----|
| 6 | Redis optional cache | [`06_CACHE.md`](06_CACHE.md) |
| 7 | SSE pub/sub migration | [`07_REALTIME.md`](07_REALTIME.md) |
| 10 | Security findings + auth plan | [`10_SECURITY.md`](10_SECURITY.md) |

---

## Implementation order

1. **Baseline** — capture production numbers before code changes (`scripts/phase1-baseline.ps1`).
2. **UnifiedEnergyState** — canonical model in `energy-core`; adapters from legacy types; no route changes required.
3. **Solar forecast snapshot** — migration `058`, write in `SnapshotWriter`, read in `GET /solar/forecast`; disable sync refresh on read by default.
4. **Financial daily aggregates** — migration `059`, shared `aggregation.py`, collector slow-lane rollup; flag off by default.
5. **Collector lanes** — split poll loop into fast/medium/slow with independent intervals and task instrumentation.
6. **Pi resilience** — LKG localStorage + connection states in frontend hook.
7. **Integration health** — migration `060`, recorder in collector prefetch, `GET /integration-health`.
8. **Observability** — `collector_task_runs` table, task summary in `/api/system/performance`, `X-Request-Id` middleware.
9. **Retention script** — `scripts/retention-policies.sql` (not applied).
10. **Re-benchmark** — post-deploy comparison in [`14_RESULTS.md`](14_RESULTS.md) (pending).

---

## Success criteria (Phase 1)

| Metric | Target p95 | Baseline (1 user) | Phase 1 mechanism |
|--------|-----------|-------------------|-------------------|
| Dashboard API | < 250 ms | 132 ms | Already OK; unchanged |
| Solar forecast | < 100 ms | 262 ms | API snapshot read path |
| Financial stats | < 300 ms | 3089 ms | Daily aggregates (flag-gated) |
| Pi snapshot | < 100 ms | UNMEASURED | LKG + 4s poll (no SSE yet) |

Full changelog: [`PHASE1_CHANGELOG.md`](../../PHASE1_CHANGELOG.md) at repo root.

---

## Migrations (058–060)

| Revision | Table(s) |
|----------|----------|
| `058_solar_forecast_api_snapshots` | `solar_forecast_api_snapshots` |
| `059_financial_daily` | `financial_daily` |
| `060_collector_tasks_integration_health` | `collector_task_runs`, `integration_health` |

Run: `alembic upgrade head` (via backend entrypoint in Docker).
