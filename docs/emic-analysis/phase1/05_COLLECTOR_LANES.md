# Collector Lanes — Fast / Medium / Slow

**Status:** Implemented  
**File:** [`collector/app/collector.py`](../../../collector/app/collector.py)

---

## Overview

The collector runs three independent asyncio loops instead of one monolithic `poll_once()`. Each lane has its own interval, timeout, and task instrumentation via `record_collector_task()`.

Compatibility: `poll_once()` still runs fast → medium → slow sequentially (used in tests).

---

## Intervals

| Lane | Interval | Config |
|------|----------|--------|
| **Fast** | Heartbeat DB setting `poll_interval_seconds` (fallback `HEARTBEAT_POLL_INTERVAL`, default **30 s**) | `_fast_lane_loop()` |
| **Medium** | **300 s** (5 min) | `COLLECTOR_MEDIUM_LANE_INTERVAL` |
| **Slow** | **900 s** (15 min) | `COLLECTOR_SLOW_LANE_INTERVAL` |

All lanes: per-task timeout `COLLECTOR_LANE_TIMEOUT_SECONDS` (default **120 s**).

---

## Fast lane (~30 s)

| Task | Description |
|------|-------------|
| Heartbeat readings | Fetch + upsert `energy_readings` |
| `market_prices` | `EmicPriceEngine.refresh_site()` per site |
| Live overview prefetch | Heartbeat live overview + integration health recording |
| `energy_balance` | Per-bridge-enabled charger energy balance |
| `snapshot_write` | `SnapshotWriter.write_all_sites()` — includes solar API snapshot |
| Smart charging | `SmartChargingEngine.run_cycle()` (separate session, outside `_run_lane`) |

---

## Medium lane (~5 min)

| Task | Description |
|------|-------------|
| `spa_integration` | Arctic Spa poll + consumer accounting (if `ARCTIC_SPA_ENABLED`) |
| `ev_accounting` | EV charger tick processing |
| `vehicle_charge_sessions` | Session coordinator |
| Energy aggregation | `EnergyAggregationService.rollup_site()` per site |
| `virtual_bridge` | Virtual Heartbeat EVSE bridge decisions |
| `ems_shadow` | EMS simulation when bridge in discovery mode |

---

## Slow lane (~15 min)

| Task | Description |
|------|-------------|
| `solar_forecast` | Observation evaluation + `SolarForecastCoordinator.run_due_sites()` |
| `forecast_learning` | `ForecastLearningService.sync_site()` |
| `energy_control` | `EnergyControlService.sync_from_strategy()` (non-monitor sites) |
| `financial_rollup:{slug}` | `FinancialAggregationService.rollup_site()` per site |

---

## Task metrics

Each `_run_lane()` call records to `collector_task_runs`: task name, lane, duration_ms, success, error_class. Summarised in `/api/system/performance` — see [`11_OBSERVABILITY.md`](11_OBSERVABILITY.md).

---

## Site poll context

[`collector/app/site_poll_context.py`](../../../collector/app/site_poll_context.py) — shared Heartbeat client + live overview prefetch per lane cycle (avoids duplicate fetches within a lane).

---

## Tests

[`collector/tests/test_collector_lanes.py`](../../../collector/tests/test_collector_lanes.py) — `poll_once()` invokes all three lanes.
