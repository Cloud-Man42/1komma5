# Cache — Design Only (Redis)

**Status:** DESIGN ONLY — no Redis in codebase  
**Reference:** [`docs/emic-analysis/05_CACHE.md`](../05_CACHE.md) (pre-Phase-1 inventory)

---

## Current state (Phase 1)

| Layer | Mechanism |
|-------|-----------|
| L1 | `InMemoryCacheService` per process ([`cache/service.py`](../../../packages/energy-core/src/energy_core/cache/service.py)) |
| L2 | DB snapshots (`site_live_snapshots`, `solar_forecast_api_snapshots`, `financial_daily`, etc.) |
| Frontend | `cache: "no-store"` on all API calls; Pi LKG in localStorage |

Baseline cache hit rate on production: **0%** in-process ([`01_BASELINE.md`](01_BASELINE.md)) — single worker / cold store.

---

## Proposed Redis layer (Phase 2+)

Optional Redis behind env flag `REDIS_URL` (not implemented).

### Key schema

| Key pattern | Value | TTL |
|-------------|-------|-----|
| `emic:snapshot:{site_slug}` | JSON site live snapshot payload | 60 s |
| `emic:dashboard:{site_slug}` | Pre-built dashboard response | 30 s |
| `emic:solar:forecast:{site_id}` | Solar forecast API snapshot JSON | 1800 s (match refresh) |
| `emic:financial:{site_id}:{period}` | Serialised financial-stats for period | 300 s |
| `emic:prices:{site_id}:current` | Current price period | 120 s |

### Invalidation

- **Write-through on collector:** `SnapshotWriter` publishes to Redis after DB upsert.
- **TTL fallback:** Keys expire naturally; no pub/sub invalidation in v1.
- **Single-flight:** Reuse existing `InMemoryCacheService` coalescing pattern at Redis miss.

### Deployment

```yaml
# docker-compose.yml (future)
redis:
  image: redis:7-alpine
  volumes: [redis_data:/data]
```

Backend + collector share `REDIS_URL`. Graceful degrade: if Redis unavailable, fall back to DB snapshot read (current behaviour).

---

## Why deferred

- Phase 1 DB snapshots already address solar forecast and financial stats bottlenecks.
- Multi-worker cache sharing requires Redis but adds ops complexity on Pi/single-host installs.
- Measure post-Phase-1 deploy before adding another layer.
