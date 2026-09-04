# Phase 12 — TimescaleDB Compression

**Deployed:** 2026-09-04 to `http://192.168.50.54`

## Goal

Enable TimescaleDB chunk compression on `energy_readings` after Phase 11 retention policies.

## Delivered

| Item | Change |
|------|--------|
| **Compression module** | `ensure_timescale_compression` in `energy_core.db.timescale_retention` |
| **Collector slow lane** | Task `timescale_compression` — idempotent enable + policy |
| **Config** | `TIMESCALE_COMPRESSION_ENABLED` (default false; enabled on prod deploy) |
| **Policy** | Compress chunks older than 7 days, segment by `site_id` |

## Flow

```
Collector slow lane (every 15 min)
  → check compression_enabled on energy_readings
  → ALTER TABLE ... SET (timescaledb.compress, compress_segmentby = site_id)
  → add_compression_policy(..., INTERVAL '7 days')
```

## Prerequisites

- Phase 11 retention policies applied
- `ENABLE_TIMESCALEDB=true` on PostgreSQL production

## Tests

- `packages/energy-core/tests/db/test_timescale_retention.py`

## Next

- Battery Opportunity Advisor (read-only)
- Horizon Optimizer
- Additional Redis keys (solar forecast, current price)
