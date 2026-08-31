# EMIC Performance Architecture v2 — Report

## Summary

Read-model snapshot layer, collector consolidation, frontend shared site data context, SSE live stream (change-detection), Performance Center with per-site snapshot age, provider circuit breaker, and request-path optimizations are in place.

Measured on production (`http://192.168.50.54`, site `akarp`, 2026-08-28).

## BEFORE / AFTER

Historical BEFORE numbers were not captured pre-v2; estimates from plan inventory are shown for context.

| View / endpoint | BEFORE p95 (ms) | AFTER p95 @ 1 user (ms) | AFTER p95 @ 10 users (ms) | Notes |
|-----------------|-----------------|-------------------------|---------------------------|-------|
| `/api/sites/akarp/dashboard` | ~800–2000 (est.) | **154** | **231** | No live Heartbeat on GET |
| `/api/sites/akarp/snapshot` | n/a | **151** | **242** | New fast path |
| `/api/sites/akarp/readings?bucket=5&hours=24` | ~500+ (est.) | **267** | **221** | CAGG when Timescale enabled |
| `/api/sites/akarp/solar/forecast` | ~5000+ (est.) | **4110** | **34034** | Still heavy under concurrency; eval moved off GET |
| Overview page request count | 9–10 | 1 layout fetch + lazy panels | — | `SiteDataProvider` |

Full baseline rows: [`baseline-results.json`](baseline-results.json).

```powershell
.\scripts\performance-baseline.ps1 -BaseUrl http://192.168.50.54 -Site akarp
```

## Architecture changes

- **Snapshot layer**: `site_live_snapshots` + collector `SnapshotWriter` + `GET /api/sites/{slug}/snapshot`
- **L1 cache**: `InMemoryCacheService` with TTL jitter and single-flight
- **Dashboard GET**: market prices from DB, no live Heartbeat
- **Solar GET**: observation evaluation in collector only
- **Collector**: one Heartbeat live overview per site via `SitePollContext`
- **Spa GET**: interval rebuild removed from HTTP path (collector only)
- **Database**: CAGG reads when `ENABLE_TIMESCALEDB=true`; `energy_hourly` / `energy_daily`
- **Frontend**: `SiteDataProvider` deduplicates dashboard; EV/energy hooks reuse shared dashboard; parallel peak fetches; `next/dynamic` for heavy Recharts panels
- **Realtime**: SSE pushes only when `generated_at` changes (1s poll)
- **Providers**: shared `httpx` client + circuit breaker + last-known-good on Heartbeat live overview
- **Observability**: Performance Center shows snapshot age per site

## Migrations

- `040_site_live_snapshots` — snapshots + energy_hourly + energy_daily

## Known remaining issues

- Multi-worker deployments still use process-local L1 cache (Redis deferred until multi-worker deploy)
- Solar forecast endpoint still slow under concurrent load — candidate for dedicated snapshot/cache
- SSE polls DB every 1s (no cross-process push from collector without Redis/NOTIFY)

## Files changed (high level)

- `packages/energy-core/src/energy_core/performance/*`
- `packages/energy-core/src/energy_core/providers/resilience.py`, `heartbeat_client.py`
- `packages/energy-core/src/energy_core/db/snapshot_repo.py`
- `collector/app/site_poll_context.py`, `collector/app/collector.py`
- `backend/app/api/snapshot.py`, `spa.py`, `system.py`
- `frontend/src/lib/SiteDataProvider.tsx`, `useEvDashboardData.ts`, `useEnergyDashboardData.ts`
- `frontend/src/app/sites/[slug]/system/performance/page.tsx`
- `docs/performance/BASELINE.md`, `baseline-results.json`, `scripts/performance-baseline.ps1`
