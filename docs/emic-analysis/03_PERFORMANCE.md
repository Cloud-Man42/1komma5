# EMIC Performance Analysis

**Baseline reference:** `docs/performance/REPORT.md` (measured 2026-08-28, site `akarp`, host `192.168.50.54`)

---

## Summary

Performance v2 introduced snapshot layer, collector consolidation, SiteDataProvider, and circuit breakers. Dashboard GET improved to p95 ~154ms. Remaining hotspots: solar forecast under concurrency, SSE DB polling, financial stats Python integration, fragmented frontend polling, and process-local cache.

Each finding uses: **Severity | FILE | FUNCTION/COMPONENT | PROBLEM | WHY | EXPECTED IMPACT | RECOMMENDED SOLUTION**

---

## DATABASE

### P-DB-01
- **Severity:** HIGH
- **FILE:** `packages/energy-core/src/energy_core/db/repositories.py`
- **FUNCTION:** `EnergyReadingRepository.list_financial_stats`
- **PROBLEM:** Loads all readings + all market prices for period into Python; pairwise interval loop
- **WHY:** No SQL-side aggregation for financial stats; O(n) memory and CPU per request
- **EXPECTED IMPACT:** Slow economy page; scales poorly with reading density (30s poll = ~2880 rows/day)
- **RECOMMENDED SOLUTION:** Pre-aggregate daily/hourly financial stats in collector; serve from rollup table

### P-DB-02
- **Severity:** MEDIUM
- **FILE:** `packages/energy-core/src/energy_core/snapshots/writer.py`
- **FUNCTION:** `SnapshotWriter.write_all_sites`
- **PROBLEM:** Reads raw readings for today integration each collector cycle
- **WHY:** Full day readings loaded per site per ~60s cycle
- **EXPECTED IMPACT:** Collector CPU/DB load grows with day length
- **RECOMMENDED SOLUTION:** Incremental snapshot update from last `generated_at`; reuse `energy_daily` rollups

### P-DB-03
- **Severity:** MEDIUM
- **FILE:** `alembic/versions/002_timescaledb.py`
- **FUNCTION:** Timescale hypertables
- **PROBLEM:** No retention/compression policy on raw `energy_readings`
- **WHY:** Migrations add CAGG but not data retention
- **EXPECTED IMPACT:** Unbounded table growth; slower queries over years
- **RECOMMENDED SOLUTION:** Timescale retention policy (e.g. raw 90d, CAGG 5y)

### P-DB-04
- **Severity:** LOW
- **FILE:** `backend/app/api/vehicles.py`
- **FUNCTION:** Multiple list endpoints
- **PROBLEM:** Several separate `.scalars().all()` queries per request
- **WHY:** No eager loading / joined queries for vehicle + state + sessions
- **EXPECTED IMPACT:** Extra DB round-trips on vehicle dashboard load
- **RECOMMENDED SOLUTION:** Single query with joins or batched repo method

---

## API / BACKEND

### P-API-01
- **Severity:** CRITICAL
- **FILE:** `backend/app/api/solar_forecast.py`
- **FUNCTION:** `get_solar_forecast` and related GET handlers
- **PROBLEM:** p95 4110ms @ 1 user, **34034ms @ 10 concurrent users** (production baseline)
- **WHY:** Heavy forecast assembly; DB reads + computation under load
- **EXPECTED IMPACT:** Solar dashboard unusable under multi-user load
- **RECOMMENDED SOLUTION:** Dedicated solar forecast snapshot in collector; GET serves precomputed JSON only

### P-API-02
- **Severity:** HIGH
- **FILE:** `backend/app/api/snapshot.py`
- **FUNCTION:** `site_live_stream`, `kiosk_stream`
- **PROBLEM:** SSE polls database every **1 second** per connection
- **WHY:** Change detection via `generated_at` comparison; no push from collector
- **EXPECTED IMPACT:** N connections × 1 QPS to DB; scales linearly with viewers
- **RECOMMENDED SOLUTION:** Redis pub/sub or PG NOTIFY from collector; or longer SSE poll interval with snapshot cache

### P-API-03
- **Severity:** MEDIUM
- **FILE:** `backend/app/display_service.py`
- **FUNCTION:** `build_display_overview`
- **PROBLEM:** Multiple repo queries + reading history for sparklines per request
- **WHY:** Aggregated endpoint still composes many data sources
- **EXPECTED IMPACT:** Pi poll every 4s amplifies backend load
- **RECOMMENDED SOLUTION:** Extend `site_live_snapshots` to include display payload; Pi reads snapshot only

### P-API-04
- **Severity:** MEDIUM
- **FILE:** `backend/app/api/dashboard.py`
- **FUNCTION:** `get_site_dashboard`
- **PROBLEM:** Complex assembly even from DB (multiple sub-computations)
- **WHY:** Large response payload with live, today, solar, economy, ev sections
- **EXPECTED IMPACT:** p95 154ms acceptable at 1 user; 231ms @ 10 users
- **RECOMMENDED SOLUTION:** Prefer `/snapshot` endpoint; slim dashboard response for overview

### P-API-05
- **Severity:** LOW
- **FILE:** `backend/app/api/readings.py`
- **FUNCTION:** `get_site_readings`
- **PROBLEM:** 24h at 5-min bucket still p95 267ms @ 1 user
- **WHY:** CAGG path depends on `ENABLE_TIMESCALEDB`; SQLite dev lacks CAGG
- **EXPECTED IMPACT:** Acceptable but improvable
- **RECOMMENDED SOLUTION:** Ensure CAGG enabled in prod; add `energy_hourly` fallback path

---

## COLLECTOR / BACKGROUND

### P-COL-01
- **Severity:** HIGH
- **FILE:** `collector/app/collector.py`
- **FUNCTION:** `poll_once`
- **PROBLEM:** ~15 sequential enrichment steps per cycle in one asyncio task
- **WHY:** Single-threaded collector does prices, spa, EV, solar, snapshots, control each cycle
- **EXPECTED IMPACT:** Long poll cycle duration; delayed snapshot freshness if one step slow
- **RECOMMENDED SOLUTION:** Split enrichment into prioritized sub-loops with different intervals

### P-COL-02
- **Severity:** MEDIUM
- **FILE:** `collector/app/collector.py`
- **FUNCTION:** `_collect_market_prices`
- **PROBLEM:** Sequential Heartbeat price refresh per site
- **WHY:** `for site in sites: await engine.refresh_site`
- **EXPECTED IMPACT:** Adds latency to enrichment cycle with multiple sites
- **RECOMMENDED SOLUTION:** Parallel refresh with concurrency limit

### P-COL-03
- **Severity:** MEDIUM
- **FILE:** `collector/app/site_poll_context.py`
- **FUNCTION:** `live_overview`
- **PROBLEM:** One Heartbeat live overview per site per cycle (good) but still blocking on slow Heartbeat
- **WHY:** Synchronous await per site in prefetch loop
- **EXPECTED IMPACT:** Collector cycle stretch when Heartbeat slow
- **RECOMMENDED SOLUTION:** Timeout per site; skip stale enrichment with LKG

---

## FRONTEND

### P-FE-01
- **Severity:** HIGH
- **FILE:** `frontend/src/lib/api.ts`
- **FUNCTION:** `apiFetch` (all calls)
- **PROBLEM:** `cache: "no-store"` on every fetch — disables HTTP caching
- **WHY:** Ensures live data but prevents browser/CDN cache
- **EXPECTED IMPACT:** Every poll hits backend; no conditional requests
- **RECOMMENDED SOLUTION:** Use cache headers on snapshot/display endpoints; ETag on `generated_at`

### P-FE-02
- **Severity:** MEDIUM
- **FILE:** `frontend/src/app/sites/[slug]/page.tsx` + `SiteDataProvider`
- **COMPONENT:** Overview
- **PROBLEM:** Dashboard fetched at 15s (page) and 30s (layout) simultaneously
- **WHY:** Independent hooks without unified coordinator
- **EXPECTED IMPACT:** 2× dashboard API calls per overview session
- **RECOMMENDED SOLUTION:** Single refresh coordinator; page uses `useOptionalSiteData` only

### P-FE-03
- **Severity:** MEDIUM
- **FILE:** `frontend/src/lib/useEconomyDashboardData.ts`
- **COMPONENT:** Economy dashboard
- **PROBLEM:** No polling despite `refreshSeconds: 60` export
- **WHY:** Missing setInterval implementation
- **EXPECTED IMPACT:** Stale economy data (opposite problem — user sees old data)
- **RECOMMENDED SOLUTION:** Add interval or document intentional static load

### P-FE-04
- **Severity:** MEDIUM
- **FILE:** `frontend/src/lib/usePiDashboardData.ts`
- **COMPONENT:** Pi kiosk
- **PROBLEM:** Poll every **4s** while backend caches overview **3s**
- **WHY:** Aggressive kiosk refresh with exponential backoff only on error
- **EXPECTED IMPACT:** ~15 requests/min per Pi; unnecessary load
- **RECOMMENDED SOLUTION:** Align poll to 5–10s; use SSE stream if available

### P-FE-05
- **Severity:** LOW
- **FILE:** `frontend/src/lib/useEnergyDashboardData.ts`
- **COMPONENT:** Energy dashboard
- **PROBLEM:** Hardcoded 60s refresh ignores site `dashboard_refresh_seconds`
- **WHY:** Not using `useDashboardRefreshSeconds`
- **EXPECTED IMPACT:** Inconsistent UX vs other dashboards
- **RECOMMENDED SOLUTION:** Use shared refresh hook

### P-FE-06
- **Severity:** LOW
- **FILE:** `frontend/src/components/*Overview.tsx`
- **COMPONENT:** Chart panels
- **PROBLEM:** Recharts re-render on every poll even if data unchanged
- **WHY:** New object references from fetch
- **EXPECTED IMPACT:** CPU on client; janky charts on Pi
- **RECOMMENDED SOLUTION:** Memoize chart data; shallow compare `generated_at`

---

## EXTERNAL API

### P-EXT-01
- **Severity:** HIGH
- **FILE:** `packages/energy-core/src/energy_core/heartbeat_client.py`
- **FUNCTION:** Heartbeat API calls
- **PROBLEM:** 20s default timeout; collector blocked on Heartbeat outage
- **WHY:** Central dependency for readings, prices, live overview
- **EXPECTED IMPACT:** Stale data across all dashboards; long collector cycles
- **RECOMMENDED SOLUTION:** Circuit breaker (partially exists) + strict per-call timeouts; degrade gracefully

### P-EXT-02
- **Severity:** MEDIUM
- **FILE:** `packages/energy-core/src/energy_core/solar_intelligence/providers/`
- **FUNCTION:** SMHI, DMI, Open-Meteo clients
- **PROBLEM:** 30s timeout each; sequential provider fallback in forecast refresh
- **WHY:** Weather fetch during collector solar cycle
- **EXPECTED IMPACT:** Collector stretch; delayed snapshots
- **RECOMMENDED SOLUTION:** Parallel provider fetch with first-success wins

### P-EXT-03
- **Severity:** MEDIUM
- **FILE:** `packages/energy-core/src/energy_core/integrations/charging_stations/chargefinder/`
- **FUNCTION:** HTTP scraping client
- **PROBLEM:** Web scraping with captcha detection; 900s cooldown on block
- **WHY:** No official API
- **EXPECTED IMPACT:** Admin lookup failures; not on critical path
- **RECOMMENDED SOLUTION:** Keep circuit breaker; cache aggressively (already 7d TTL)

---

## CACHE

### P-CACHE-01
- **Severity:** HIGH
- **FILE:** `packages/energy-core/src/energy_core/cache/service.py`
- **FUNCTION:** `InMemoryCacheService`
- **PROBLEM:** Process-local L1 only — ineffective with multiple uvicorn workers
- **WHY:** No Redis/shared cache (deferred in performance report)
- **EXPECTED IMPACT:** Cache misses per worker; duplicated Heartbeat protection
- **RECOMMENDED SOLUTION:** Redis or memcached for snapshot + LKG when scaling workers

### P-CACHE-02
- **Severity:** MEDIUM
- **FILE:** `backend/app/display_service.py`
- **FUNCTION:** Module-level `_OVERVIEW_CACHE`
- **PROBLEM:** In-memory dict not shared across workers
- **WHY:** Same as L1 cache limitation
- **EXPECTED IMPACT:** Pi requests may hit cold worker
- **RECOMMENDED SOLUTION:** DB snapshot for display payload

---

## NETWORK / RENDERING

### P-NET-01
- **Severity:** MEDIUM
- **FILE:** `frontend/next.config.js`
- **COMPONENT:** Bundle
- **PROBLEM:** Multiple CSS domain modules loaded in root layout (energy, solar, ev, spa, economy, pi)
- **WHY:** Global imports in `layout.tsx`
- **EXPECTED IMPACT:** Larger initial bundle; slower first paint on Pi
- **RECOMMENDED SOLUTION:** Route-level CSS splitting (partially done for display layout)

### P-NET-02
- **Severity:** LOW
- **FILE:** `frontend/src/lib/api.ts`
- **FUNCTION:** `apiFetch` duplicate detection
- **PROBLEM:** Warns on duplicate URL within 2s only when `NEXT_PUBLIC_PERFORMANCE_DEBUG=1`
- **WHY:** Debug-only guard
- **EXPECTED IMPACT:** Duplicates go unnoticed in production
- **RECOMMENDED SOLUTION:** Enable lightweight dedup/coalesce in production for same slug endpoints

---

## Measured Baseline (Production, 2026-08-28)

| Endpoint | p95 @ 1 user | p95 @ 10 users |
|----------|--------------|----------------|
| `/api/sites/akarp/dashboard` | 154 ms | 231 ms |
| `/api/sites/akarp/snapshot` | 151 ms | 242 ms |
| `/api/sites/akarp/readings?bucket=5&hours=24` | 267 ms | 221 ms |
| `/api/sites/akarp/solar/forecast` | 4110 ms | **34034 ms** |

Script: `scripts/performance-baseline.ps1`

---

## Blocking I/O Summary

| Pattern | Location | Async? |
|---------|----------|--------|
| SQLAlchemy async | All repos | Yes |
| httpx async | Heartbeat, Charge Amps, weather | Yes |
| Mercedes WebSocket | collector supervisor | Yes |
| SSE generator sleep | snapshot.py | Async sleep 1s |
| Frontend fetch | api.ts | Non-blocking but serial awaits in hooks |

**Sequential async chains:** Overview hook awaits multiple fetches — should use `Promise.all` (verify per hook; `useOverviewData` uses parallel pattern).

---

## Polling Frequency Summary

| Client | Interval | Endpoint |
|--------|----------|----------|
| Pi kiosk | 4s (→30s backoff) | display overview |
| Overview page dashboard | 15s | dashboard |
| Site layout | 30s | dashboard |
| Overview extra data | 60s | solar/history |
| Energy dashboard | 60s | dashboard/readings |
| Performance center | 10s | system/performance |
| SSE live stream | 1s DB poll | snapshot |
| Collector | 30–60s | Heartbeat ingest |

**Assessment:** EMIC does significant real-time work on the client; collector-snapshot-push model would reduce load (see `08_REALTIME_DATA.md`).
