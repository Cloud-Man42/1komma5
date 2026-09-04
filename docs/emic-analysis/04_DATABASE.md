# EMIC Database Analysis

**ORM models:** `packages/energy-core/src/energy_core/db/models.py`  
**Migrations:** `alembic/versions/` (001 → 057)  
**Repositories:** 31 files in `packages/energy-core/src/energy_core/db/`

---

## 1. Database Engines

| Environment | Engine | URL pattern |
|-------------|--------|-------------|
| Development | SQLite (aiosqlite) | `sqlite+aiosqlite:///./energy-dev.db` |
| Production | PostgreSQL 16 + TimescaleDB | `postgresql+asyncpg://...@postgres:5432/energy` |
| Tests | SQLite temp | `backend/tests/conftest.py` |

Detection: `Settings.is_sqlite`, `Settings.is_postgresql` in `energy_core/config.py`  
Alembic batch mode for SQLite: `alembic/env.py`

---

## 2. Schema Overview (~60 Tables)

### 2.1 Core Site & Time-Series

| Table | PK | Purpose | Growth rate |
|-------|-----|---------|-------------|
| `sites` | `id` | Root entity, economics config | Static |
| `energy_readings` | `(site_id, recorded_at)` | Site power time-series (~30–60s) | **HIGH** |
| `heartbeat_settings` | `id` | Poll/refresh config | Static |
| `site_live_snapshots` | `(site_id, generated_at)` | Precomputed dashboard JSON | **MEDIUM** |
| `energy_hourly` | `(site_id, hour)` | App rollup | LOW |
| `energy_daily` | `(site_id, day)` | App rollup | LOW |

**`energy_readings` columns (W unless noted):**
- `solar_production_w`, `consumption_w`
- `grid_import_w`, `grid_export_w`
- `battery_soc_pct`, `battery_power_w`
- Optional: `ev_power_w`, `battery_charge_w`, `battery_discharge_w`

### 2.2 Pricing

| Table | Granularity | Status |
|-------|-------------|--------|
| `market_prices` | Hourly (legacy) | Active for financial stats |
| `price_periods` | 15-min | Canonical price engine store |
| `price_engine_state` | Per site | Refresh metadata |
| `energy_forecast_snapshots` | Per period/kind | Forecast learning |

Retention: `price_periods` **90 days** (`price_engine/engine.py RETENTION_DAYS=90`)

### 2.3 EV / Charging

| Table | Purpose |
|-------|---------|
| `ev_chargers` | Physical/virtual chargers |
| `ev_charging_sessions` | Session energy + cost attribution |
| `ev_charging_intervals` | Sub-session intervals |
| `battery_energy_ledger` | Solar vs grid battery energy |
| `ev_bridge_cycles` | Smart charging ticks (**HIGH** growth) |

### 2.4 Solar (15+ tables)

Key tables: `solar_site_configurations`, `solar_forecast_runs`, `solar_forecast_points`, `solar_forecast_observations`, `solar_forecast_hourly`, `solar_radiation_samples`, `solar_training_samples`, `solar_models`, `solar_weather_cache`, `solar_performance_daily`, `solar_provider_health`

Retention: forecast runs **14 days** (`SOLAR_FORECAST_RETENTION_DAYS`)

### 2.5 Spa / Consumers

| Table | Purpose | Timescale |
|-------|---------|-----------|
| `energy_consumers` | Consumer registry | — |
| `consumer_samples` | Power samples | Hypertable (PG) |
| `consumer_intervals` | Integrated intervals | — |
| `consumer_aggregates` | hourly/daily/monthly | — |
| `spa_*` | Config, poll state, events, control | — |
| `flexible_load_plan(_block)` | SPA scheduling | — |

### 2.6 Vehicles

| Table | Purpose | Growth |
|-------|---------|--------|
| `vehicle_provider_connections` | Encrypted credentials | Static |
| `vehicles`, `vehicle_capabilities` | Registry | Static |
| `vehicle_state_latest` | Current state | Static |
| `vehicle_state_history` | Telemetry history | **HIGH** (hypertable) |
| `vehicle_charge_sessions` | Sessions | MEDIUM |
| `vehicle_attribute_observations` | Raw attributes | **HIGH** |
| `vehicle_integration_events` | Events (14d retention) | MEDIUM |

### 2.7 Heartbeat Bridge / Virtual EVSE

`heartbeat_discovery_runs`, `heartbeat_api_observations`, `heartbeat_ev_mappings`, `heartbeat_bridge_settings`, `virtual_charger_decisions`, `virtual_charger_commands`, `virtual_charger_replay_runs`

### 2.8 Other

`apple_devices`, `charging_station`, `charging_station_lookup_cache`, `chargefinder_integration_status`, `energy_balance_snapshots`, `historical_monthly_energy`, `site_energy_config`

**Dropped legacy:** `energy_devices` (migration 012 — Modbus removed)

---

## 3. Relationships

- **Hub:** Almost all tables FK → `sites.id` ON DELETE CASCADE
- **EV:** `ev_chargers.site_id` → sites; sessions → chargers
- **Consumers:** `consumer_samples.consumer_id` → `energy_consumers`
- **Vehicles:** `vehicles.site_id` → sites; state history → vehicles

---

## 4. Indexes

Notable indexes (from migrations + models):
- `ix_energy_readings_recorded_at`
- `ix_price_periods_site_period`
- `ix_site_live_snapshots_generated_at`
- `ix_energy_hourly_site_hour`, `ix_energy_daily_site_day`
- `ix_consumer_samples_consumer_recorded`
- `ix_ev_charging_sessions_charger_started`
- `042_query_performance_indexes.py` — session status indexes
- `ix_energy_control_actions` — site_id on actions

**Potential gaps:**
- `energy_readings` queries by `site_id + time range` — composite PK helps but long-range scans remain expensive without CAGG
- `vehicle_attribute_observations` — growth table; index coverage UNKNOWN for all query paths

---

## 5. TimescaleDB Features

Migration `002_timescaledb.py`:
- Hypertable: `energy_readings(recorded_at)`
- Continuous aggregates: `energy_readings_5min`, `energy_readings_1hour`
- Refresh policies: 5 min / 1 hour

Migration `023`: hypertable `consumer_samples(recorded_at)`  
Migration `027`: hypertable `vehicle_state_history(recorded_at)`

**Gated by:** `ENABLE_TIMESCALEDB=true` (production docker-compose)

**Repository CAGG path:** `EnergyReadingRepository._list_aggregated_cagg` in `repositories.py`

---

## 6. Aggregation Layers

1. **Timescale CAGG** (PG only): 5-min, 1-hour buckets
2. **Application rollups:** `EnergyAggregationService` — last 48h → `energy_hourly`; today → `energy_daily`
3. **Consumer aggregates:** hourly/daily/monthly/yearly in `consumer_aggregates`
4. **Power→kWh:** trapezoid integration, max gap 300s (`energy/integration.py`)
5. **Financial stats:** Python pairwise loop over raw readings (`list_financial_stats`) — **not pre-aggregated**

---

## 7. Retention Policies

| Data | Retention | Source |
|------|-----------|--------|
| Solar forecast runs | 14 days | `SOLAR_FORECAST_RETENTION_DAYS` |
| Price periods | 90 days | `price_engine/engine.py` |
| Vehicle integration events | 14 days | `integration_event_repo.py` |
| ChargeFinder cache | 7 days TTL | config |
| Raw energy_readings | **None explicit** | — |
| consumer_samples | **None explicit** | — |
| vehicle_state_history | **None explicit** | — |

---

## 8. Data Duplication

| Duplication | Tables involved |
|-------------|-----------------|
| Hourly prices | `market_prices` + `price_periods` (different granularity) |
| Dashboard data | `site_live_snapshots` duplicates computed view of readings + prices |
| Solar forecast | `solar_forecast_points`, `solar_forecast_hourly`, `solar_daily_forecast_snapshots` |
| Vehicle state | `vehicle_state_latest` + `vehicle_state_history` (intentional) |
| EV sessions | `ev_charging_sessions` + `vehicle_charge_sessions` (charger vs vehicle centric) |

---

## 9. Inefficient Query Patterns

| Pattern | File | Issue |
|---------|------|-------|
| Full period readings load | `repositories.py:list_financial_stats` | All rows to Python |
| Snapshot writer daily readings | `snapshots/writer.py` | Full day each cycle |
| SSE 1s snapshot read | `snapshot.py` | Repeated latest snapshot query |
| Solar forecast GET assembly | `solar_forecast.py` | Heavy read under concurrency |

---

## 10. Optimization Opportunities

| Opportunity | Benefit |
|-------------|---------|
| Timescale compression on `energy_readings` | Storage 5y+ |
| Retention: raw 90d, CAGG 5y | Bounded growth |
| Materialized daily financial stats | Fast economy API |
| Snapshot-only GET paths | Remove repeated computation |
| Partial indexes on active sessions | Faster EV queries |

---

## 11. Database Suitability Assessment

### 1 Year
**Adequate** with current PostgreSQL + TimescaleDB. ~1M readings/site/year at 60s poll. CAGG handles chart queries. Monitor disk if retention not configured.

### 3 Years
**Marginal** without retention/compression. Raw readings ~3M+/site; `vehicle_state_history`, `consumer_samples`, `ev_bridge_cycles` add significant volume. Financial stats Python integration will degrade.

### 5 Years
**Requires policy changes.** Recommend:
- Timescale retention + compression
- Archive cold data or object storage export
- Pre-aggregated economics and daily energy summaries
- Consider dedicated TSDB (Timescale is appropriate if policies applied)

**SQLite:** Not suitable for production multi-year; dev/test only.

---

## 12. Unused / Low-Use Tables (Candidates for Review)

| Table | Notes |
|-------|-------|
| `nobil_integration_status` | Migration 051; ChargeFinder may supersede |
| `historical_monthly_energy` | Manual entry; usage frequency UNKNOWN |
| `energy_devices` | Dropped from models |
| `solar_forecast_model_profiles` | v1 legacy alongside v2 intelligence |

Verification requires production query analytics — marked **UNKNOWN** for actual usage frequency.
