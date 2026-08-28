# EMIC Performance Architecture v2 — Report

## Summary

Implemented read-model snapshot layer, request-path instrumentation, collector consolidation, Timescale CAGG wiring, frontend shared site data context, SSE live stream, and Performance Center admin view.

## BEFORE / AFTER

Run baseline before/after deploy to populate real numbers:

```powershell
.\scripts\performance-baseline.ps1 -BaseUrl http://localhost:8000 -Site akarp
```

| View / endpoint | BEFORE p95 (ms) | AFTER p95 (ms) | Change |
|-----------------|-----------------|----------------|--------|
| `/api/sites/akarp/dashboard` | _measure_ | _measure_ | |
| `/api/sites/akarp/snapshot` | n/a | _measure_ | new fast path |
| `/api/sites/akarp/solar/forecast` | _measure_ | _measure_ | no eval on GET |
| Overview page request count | 9–10 | 1 layout fetch + lazy panels | |

## Architecture changes

- **Snapshot layer**: `site_live_snapshots` table + collector `SnapshotWriter` + `GET /api/sites/{slug}/snapshot`
- **L1 cache**: `InMemoryCacheService` with TTL jitter and single-flight
- **Dashboard GET**: market prices from DB, no live Heartbeat
- **Solar GET**: observation evaluation in collector only
- **Collector**: one Heartbeat live overview per site via `SitePollContext`
- **Database**: CAGG reads when `ENABLE_TIMESCALEDB=true`; `energy_hourly` / `energy_daily` pre-aggregation
- **Frontend**: `SiteDataProvider` deduplicates dashboard polling; `useSiteCache` for SWR-style TTL
- **Realtime**: `GET /api/sites/{slug}/live-stream` SSE + kiosk endpoints
- **Observability**: `PerformanceMiddleware`, SQL slow-query log, `/api/system/performance`

## Migrations

- `040_site_live_snapshots` — snapshots + energy_hourly + energy_daily

## Known remaining issues

- Multi-worker deployments still use process-local L1 cache (Redis not added until measured need)
- SSE uses polling interval internally; true push from collector not yet wired
- Performance Center snapshot age per site not yet surfaced in UI

## Files changed (high level)

- `packages/energy-core/src/energy_core/performance/*`
- `packages/energy-core/src/energy_core/cache/service.py`
- `packages/energy-core/src/energy_core/snapshots/writer.py`
- `packages/energy-core/src/energy_core/db/snapshot_repo.py`
- `packages/energy-core/src/energy_core/aggregation/service.py`
- `collector/app/site_poll_context.py`, `collector/app/collector.py`
- `backend/app/api/snapshot.py`, `dashboard.py`, `system.py`, `main.py`
- `frontend/src/lib/SiteDataProvider.tsx`, `useSiteCache.ts`, site layout
- `docs/performance/BASELINE.md`, `scripts/performance-baseline.ps1`
