# Phase 9 — Display Overview SSE Pub/Sub

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Goal

Stop polling the database every 1 s on the Pi display SSE endpoint when Redis snapshot events are available.

## Delivered

| Item | Change |
|------|--------|
| **Shared channel** | Reuses Phase 8 `emic:events:snapshot:{site_id}` notifications |
| **Display SSE** | `/api/v1/display/overview/{slug}/stream` subscribes and rebuilds overview on push |
| **Graceful degrade** | Falls back to 1 s poll loop if Redis is down or listener errors |
| **Auth unchanged** | Still requires display device token (`display.read` scope) |

## Flow

```
Collector SnapshotWriter → PUBLISH emic:events:snapshot:{site_id}

Pi display EventSource → display overview SSE
  → initial DisplayOverviewService.build()
  → SUBSCRIBE snapshot channel → rebuild overview on event
  → fallback: poll build() every 1 s
```

Display payload is still built in the backend (not inlined in Redis) because it aggregates dashboard, weather, EV, spa, etc.

## Tests

- `backend/tests/test_display_api.py` — SSE generator emits initial chunk with poll fallback

## Next

- Dashboard/financial Redis keys per `06_CACHE.md`
- Retention policies per `12_DATABASE_RETENTION.md`
