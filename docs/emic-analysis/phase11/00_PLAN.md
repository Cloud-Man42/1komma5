# Phase 11 — TimescaleDB Retention Policies

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Goal

Automate raw data lifecycle on production PostgreSQL/TimescaleDB per `12_DATABASE_RETENTION.md`.

## Delivered

| Item | Change |
|------|--------|
| **Retention module** | `energy_core.db.timescale_retention.ensure_timescale_retention` |
| **Collector slow lane** | Task `timescale_retention` — idempotent policy ensure |
| **Config** | `TIMESCALE_RETENTION_ENABLED` (default false; enabled on prod deploy) |
| **Policies** | `energy_readings` 90d, `consumer_samples` 90d, `vehicle_state_history` 180d |

## Prerequisites

- `ENABLE_TIMESCALEDB=true` on PostgreSQL production
- `financial_daily` backfill complete before shortening raw retention window

## Tests

- `packages/energy-core/tests/db/test_timescale_retention.py`

## Notes

- `energy_hourly` / `energy_daily` are regular tables — not managed by Timescale retention jobs
- Compression policy remains manual in `scripts/retention-policies.sql`

## Roadmap complete

Phases 5–11 of the EMIC performance/security roadmap are deployed. Phase 12 adds compression.

Further work: Battery Opportunity Engine, Horizon Optimizer, additional Redis cache keys.
