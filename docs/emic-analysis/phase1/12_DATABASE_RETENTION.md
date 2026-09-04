# Database Retention

**Status:** Recommendations + script only — **NOT APPLIED**

---

## Rationale

`energy_readings` and related tables grow without bound. Full-table scans (financial stats baseline) and index size affect query latency. TimescaleDB retention policies automate pruning on PostgreSQL production.

Phase 1 adds **pre-aggregated** tables (`financial_daily`, `solar_forecast_api_snapshots`) that reduce dependence on raw readings for hot paths — but raw data still needs lifecycle management.

---

## Script

**File:** [`scripts/retention-policies.sql`](../../../scripts/retention-policies.sql)

All statements are **commented out** — review and run manually after backup.

| Table | Proposed retention |
|-------|-------------------|
| `energy_readings` | 90 days |
| `consumer_samples` | 90 days |
| `vehicle_state_history` | 180 days |
| `energy_hourly` | 730 days (2 years) |
| `energy_daily` | Indefinite |
| `financial_daily` | Indefinite (Phase 1 aggregate) |

Compression policy (commented): compress `energy_readings` after 7 days with `compress_segmentby = 'site_id'`.

---

## Prerequisites

- `ENABLE_TIMESCALEDB=true` on production PostgreSQL
- Verified backup procedure
- Backfill `financial_daily` before shortening raw readings retention below aggregate window

---

## Application-level retention (existing)

| Setting | Default | Table |
|---------|---------|-------|
| `SOLAR_FORECAST_RETENTION_DAYS` | 14 | Solar forecast history |
| Collector task runs | 48 h | Auto-prune in `task_metrics.py` |

---

## Phase 1 action

Document only. No migration or cron job added. Apply in Phase 2 after capacity review and aggregate backfill validation.

---

## Rollback

Retention policies are drop-in via `remove_retention_policy()`. Keep backups before first application.
