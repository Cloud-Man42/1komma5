# Solar Forecast API Snapshot

**Status:** Implemented  
**Migration:** `058_solar_forecast_api_snapshots`

---

## Problem

`GET /api/sites/{slug}/solar/forecast` previously triggered synchronous forecast refresh on stale reads (`solar_forecast_sync_refresh_on_read=true` in some deployments), causing p95 ~262 ms at 1 user and historical ~5 s spikes. Target: **p95 < 100 ms** via pre-built JSON snapshot.

Baseline: [`01_BASELINE.md`](01_BASELINE.md) — solar forecast p95 **261.6 ms** at 1 user.

---

## Table: `solar_forecast_api_snapshots`

| Column | Type | Purpose |
|--------|------|---------|
| `site_id` | PK, FK → `sites` | One row per site |
| `generated_at` | timestamptz | When snapshot row was written |
| `forecast_generated_at` | timestamptz | Source forecast timestamp |
| `freshness` | varchar(16) | `LIVE` / `FRESH` / `STALE` / `DEGRADED` |
| `payload_json` | text | Full API response JSON |

Index: `ix_solar_forecast_api_snapshots_generated_at`.

**Files:** [`alembic/versions/058_solar_forecast_api_snapshots.py`](../../../alembic/versions/058_solar_forecast_api_snapshots.py), [`db/models.py`](../../../packages/energy-core/src/energy_core/db/models.py) (`SolarForecastApiSnapshotModel`).

---

## Write path (collector)

1. Fast lane runs `SnapshotWriter.write_all_sites()` ([`snapshots/writer.py`](../../../packages/energy-core/src/energy_core/snapshots/writer.py)).
2. For each site with solar config enabled, loads latest forecast from `SolarForecastRepository`.
3. Builds API payload via [`api_snapshot_builder.py`](../../../packages/energy-core/src/energy_core/solar_forecast/api_snapshot_builder.py).
4. Upserts via `SolarForecastApiSnapshotRepository.upsert()` with freshness derived from `SOLAR_FORECAST_REFRESH_MINUTES` (default 30 min).

---

## Read path (API)

**Route:** `GET /api/sites/{slug}/solar/forecast` — [`backend/app/api/solar_forecast.py`](../../../backend/app/api/solar_forecast.py)

1. `load_solar_forecast_snapshot()` ([`api_read.py`](../../../packages/energy-core/src/energy_core/solar_forecast/api_read.py)) reads pre-built JSON; recalculates age/freshness at read time.
2. If snapshot exists → `payload_to_solar_forecast_response()` — **no DB forecast computation**.
3. Fallback → `_resolve_forecast()` (legacy path) only when snapshot missing.

---

## Flag: `SOLAR_FORECAST_SYNC_REFRESH_ON_READ`

| Setting | Default | Alias |
|---------|---------|-------|
| `solar_forecast_sync_refresh_on_read` | **`false`** | `SOLAR_FORECAST_SYNC_REFRESH_ON_READ` |

Defined in [`config.py`](../../../packages/energy-core/src/energy_core/config.py).

When `false` (recommended production):
- Read path never blocks on Open-Meteo / coordinator refresh.
- Stale forecast served from snapshot or DB row until collector slow lane refreshes.

When `true` (legacy/debug):
- `_resolve_forecast()` may call `SolarForecastCoordinator.refresh_site_now()` or `SolarIntelligenceCoordinator.refresh_site()` on stale reads.

---

## Repository

[`db/solar_api_snapshot_repo.py`](../../../packages/energy-core/src/energy_core/db/solar_api_snapshot_repo.py) — upsert with SQLite/Postgres conflict handling; `_freshness_from_age()` thresholds: LIVE ≤120 s, FRESH ≤ stale_after, STALE ≤ 3× stale_after, else DEGRADED.

---

## Tests

[`backend/tests/test_solar_forecast_snapshot_api.py`](../../../backend/tests/test_solar_forecast_snapshot_api.py) — snapshot served without refresh, 404/503 paths, stale snapshot behaviour.
