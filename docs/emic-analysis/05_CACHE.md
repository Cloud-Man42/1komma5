# EMIC Cache Analysis

---

## 1. Cache Inventory

### 1.1 In-Process Memory Cache (L1)

| Property | Value |
|----------|-------|
| **File** | `packages/energy-core/src/energy_core/cache/service.py` |
| **Class** | `InMemoryCacheService` |
| **Features** | TTL jitter (±10%), single-flight coalescing on miss |
| **Scope** | Per process (uvicorn worker / collector) |
| **Used by** | Snapshot routes, site dashboard cache |

**Limitation:** Not shared across workers (documented in `docs/performance/REPORT.md`).

### 1.2 Database Snapshots

| Table | Writer | Reader | Effective TTL |
|-------|--------|--------|---------------|
| `site_live_snapshots` | `snapshots/writer.py` (collector) | `/snapshot`, `/dashboard` | Collector poll interval (~30–60s) |
| `energy_hourly` / `energy_daily` | `aggregation/service.py` | History, dashboard | Updated each collector cycle |
| `solar_weather_cache` | Solar forecast coordinator | Solar weather GET | 45 min config |
| `solar_daily_forecast_snapshots` | Solar intelligence | Forecast endpoints | Refresh cycle |
| `energy_forecast_snapshots` | Forecast learning | Learning API | Per prediction window |
| `energy_balance_snapshots` | Energy balance coordinator | Diagnostics | Per collector cycle |
| `charging_station_lookup_cache` | ChargeFinder | Lookup API | 7 days |

### 1.3 Backend Route Caches

| Cache | TTL | File |
|-------|-----|------|
| Widget snapshot | 15s (`WIDGET_SNAPSHOT_CACHE_SECONDS`) | `backend/app/widget_service.py` |
| Display overview | 3s | `backend/app/display_service.py` `_OVERVIEW_CACHE` |
| Display weather | 60s | `display_service.py` `_WEATHER_CACHE` |
| Snapshot route | 5s (documented in snapshot flow) | `backend/app/api/snapshot.py` |

### 1.4 Provider Resilience Cache

| Mechanism | File | Behavior |
|-----------|------|----------|
| `LastKnownGoodStore` | `providers/resilience.py` | In-memory per-key with max_age |
| Heartbeat LKG | `heartbeat_client.py` | Used with circuit breaker on live overview |
| Solar intelligence LKG | `solar_intelligence/engine.py` | Degraded forecast from last good |
| Vehicle state LKG merge | `db/vehicle_repo.py` `_merge_last_known_good` | Keeps recent charging values when stale |

### 1.5 Frontend Caches

| Mechanism | Location | Behavior |
|-----------|----------|----------|
| `SiteDataProvider` | `SiteDataProvider.tsx` | Shared in-memory dashboard state |
| `SolarLayoutContext` | `SolarLayoutContext.tsx` | Shared solar config/weather |
| `cache: "no-store"` | `api.ts` | **Disables** HTTP cache on all API calls |
| Theme localStorage | `ThemeProvider.tsx` | UI preference |
| Energy scene IndexedDB | `energyScenePhotoStore.ts` | Custom photos |
| Pi backoff state | `usePiDashboardData.ts` | In-hook, not data cache |

**No SWR, React Query, or service worker cache.**

---

## 2. Recommended Cache Strategy by Data Source

| Data source | Recommended TTL | Current EMIC behavior | Gap |
|-------------|-----------------|-------------------------|-----|
| Live inverter power | 1–5 sec | Snapshot ~30–60s via collector | Coarser than ideal for true live |
| Battery SOC | 5–15 sec | Same as readings | Acceptable via snapshot |
| Battery power | 1–5 sec | Same | Acceptable |
| Grid import/export | 1–5 sec | Same | Acceptable |
| House consumption | 5–15 sec | Same | Acceptable |
| EV charger power | 5–15 sec | Collector + smart charging cycle | OK |
| Vehicle SOC/location | 30–300 sec | Adaptive Mercedes poll | OK |
| Weather (current) | 10–30 min | 45 min cache | OK |
| Solar forecast (today) | 15–60 min | 30 min refresh | OK |
| Solar forecast (tomorrow) | 1–4 hours | 30 min refresh | Slightly aggressive |
| Nord Pool / import price | 15 min (period aligned) | Collector price engine refresh | OK |
| Export price | 15 min – 1 hour | Same | OK |
| Historical statistics (24h charts) | 1–5 min | Readings GET uncached | **Gap** — should use CAGG + cache |
| Daily energy totals | 1–5 min | Snapshot | OK |
| Financial stats (day) | 5–15 min | Uncached Python compute | **Gap** |
| Economy YTD | 1 hour | Mount-only, no refresh | **Gap** |
| Spa status | 30–60 sec | 60s Arctic poll | OK |
| Spa energy today | 1–5 min | Consumer aggregates | OK |
| ChargeFinder stations | 1–7 days | 7 days | OK |
| Heartbeat live overview | 15–30 sec | 1× per collector cycle | OK (not per client) |
| Dashboard JSON | 5–30 sec | Snapshot + L1 | OK |
| Pi display overview | 5–10 sec | 3s server + 4s client poll | Over-polling |
| Performance metrics | 10 sec | 10s frontend poll | OK |
| Forecast learning summary | 15–60 min | Mount only | Under-utilized |

---

## 3. Cache Coherence Issues

1. **Multi-worker L1:** Each uvicorn worker has separate `InMemoryCacheService` — cache hit rate divided by worker count.
2. **Frontend no-store:** Browser never caches API responses even when `generated_at` unchanged.
3. **Pi 4s poll vs 3s server cache:** Client often misses server cache benefit.
4. **SSE 1s DB poll:** Bypasses L1 cache for stream clients.
5. **Economy static load:** No cache benefit because page doesn't refresh.

---

## 4. Real-Time Work Assessment

**Does EMIC do too much real-time work?**

**Yes, on the client side:**
- Multiple dashboards poll independently (15s, 30s, 60s, 4s Pi)
- No shared WebSocket push (except SSE snapshot stream, rarely used by main dashboards)
- Each browser tab runs full poll suite

**No, on the server ingestion side (post v2):**
- Collector centralizes Heartbeat polling
- Dashboard GET does not call Heartbeat live
- Live overview fetched once per site per collector cycle

**Recommended model:**
```
Device/API → Collector → Normalized state → DB snapshot + L1/Redis → SSE/WebSocket → Client (single subscription)
```

Current EMIC is **hybrid:** collector-centralized ingestion but **client-decentralized** refresh.

---

## 5. HTTP Cache Headers

**Current:** No Cache-Control/ETag on API responses (except implicit via FastAPI defaults).

**Recommendation:**
- `GET /api/sites/{slug}/snapshot` → `ETag: {generated_at}`, `Cache-Control: max-age=5`
- `GET /api/v1/display/overview/{slug}` → `max-age=3`
- Static Next.js assets → already cached by browser

---

## 6. Missing Cache Layers

| Layer | Status |
|-------|--------|
| Redis / Memcached | Not implemented (deferred) |
| CDN edge cache | N/A (LAN/private deployment) |
| Browser HTTP cache | Disabled via no-store |
| React Query / SWR | Not used |
| DB query result cache | Not used |
| Materialized views (financial) | Not implemented |

---

## 7. Cache Invalidation

| Trigger | Invalidation |
|---------|--------------|
| New collector reading | Upsert readings; snapshot rewritten next cycle |
| Price engine refresh | Upsert price_periods |
| Config change | No explicit cache purge — L1 expires by TTL only |
| Manual site config PUT | May serve stale snapshot until next collector cycle |

**Gap:** No explicit cache invalidation on config updates.

---

## 8. Summary

EMIC has a **solid collector-side snapshot strategy** (Performance v2) but **weak client-side and multi-worker caching**. Highest-impact improvements:
1. Shared Redis for L1 + SSE pub/sub
2. ETag on snapshot/display endpoints
3. Pre-computed financial stats (avoid repeated Python integration)
4. Unified frontend poll coordinator
5. Timescale retention to cap DB cache working set
