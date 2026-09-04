# Phase 8 — Redis SSE Pub/Sub

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Goal

Replace 1 s DB polling in snapshot live-stream SSE with Redis pub/sub push from the collector, with poll fallback when Redis is unavailable.

## Delivered

| Item | Change |
|------|--------|
| **Pub/sub module** | `energy_core.cache.snapshot_pubsub` — publish/subscribe on `emic:events:snapshot:{site_id}` |
| **Collector push** | `SnapshotWriter` publishes full snapshot payload after cache write-through |
| **SSE subscribe** | `/api/sites/{slug}/live-stream` and `/api/kiosk/{slug}/stream` subscribe when Redis is up |
| **Graceful degrade** | Falls back to 1 s poll loop if Redis is down or listener errors |
| **Observability** | Performance Center cache block includes `snapshot_pubsub_configured` / `snapshot_pubsub_available` |

## Flow

```
Collector SnapshotWriter
  → UPSERT site_live_snapshots
  → cache.set (L1+L2)
  → PUBLISH emic:events:snapshot:{site_id}

Backend SSE (_snapshot_sse_generator)
  → initial _load_snapshot
  → SUBSCRIBE (push updates inline, no DB read)
  → fallback: poll _load_snapshot every 1 s
```

## Configuration

Uses existing `REDIS_URL` from Phase 7. No new env vars.

## Tests

- `packages/energy-core/tests/cache/test_snapshot_pubsub.py`
- `packages/energy-core/tests/solar_forecast/test_snapshot_writer_cache.py` (publish on write)
- `backend/tests/test_snapshot_api.py` (SSE first chunk + performance fields)

## Next

- Display overview stream pub/sub (separate channel or shared notification)
- Dashboard/financial Redis keys
- Retention policies
