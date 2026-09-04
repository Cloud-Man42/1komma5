# EMIC Background Jobs

**No Celery, APScheduler, cron, or FastAPI background tasks.** All scheduled work runs in the **collector process** (`collector/app/collector.py`) and **VehicleIntegrationSupervisor**.

---

## 1. Collector Main Loop

| Property | Value |
|----------|-------|
| **Entry** | `collector/app/__main__.py` → `Collector.run()` |
| **Interval** | DB `heartbeat_settings.poll_interval_seconds` (default 30–60s); fallback `HEARTBEAT_POLL_INTERVAL` |
| **Signals** | SIGINT/SIGTERM stop loop |
| **Concurrency** | Single asyncio loop; sequential enrichment |

### 1.1 `poll_once()` Steps (in order)

| Step | Function | Data read | Data written | Duration risk |
|------|----------|-----------|--------------|---------------|
| 1 | Heartbeat `fetch_readings` | Heartbeat API | `energy_readings` | Heartbeat latency |
| 2 | `_collect_market_prices` | Heartbeat prices | `price_periods`, `market_prices` | Per-site sequential |
| 3 | `_prefetch_live_overviews` | Heartbeat live overview (1×/site) | In-memory dict | Heartbeat latency |
| 4 | `_run_spa_integration` | Arctic Spa API | `consumer_samples`, spa state | Optional |
| 5 | `_run_ev_accounting` | Live overview + readings | EV sessions, intervals, ledger | Medium |
| 6 | `_run_vehicle_charge_sessions` | Live overview | `vehicle_charge_sessions` | Medium |
| 7 | `_run_energy_balance` | Sungrow/Halo/Heartbeat | `energy_balance_snapshots` | Medium |
| 8 | `_run_solar_forecast` | Weather APIs | Solar forecast tables | **HIGH** (30s timeouts) |
| 9 | `_run_forecast_learning` | Forecasts + actuals | `energy_forecast_snapshots` | Low |
| 10 | `_run_energy_control` | Price strategy | `energy_control_actions` | Low |
| 11 | `_energy_aggregation.rollup_site` | Raw readings | `energy_hourly`, `energy_daily` | Medium |
| 12 | `_snapshot_writer.write_all_sites` | Readings, prices, etc. | `site_live_snapshots` | Medium |
| 13 | `_charging_engine.run_cycle` | EnergyState + Charge Amps | Charger control, `ev_bridge_cycles` | Charge Amps writes |
| 14 | `_run_virtual_bridge_cycle` | Heartbeat bridge | Virtual charger decisions/commands | Medium |
| 15 | `_run_ems_shadow_simulation` | Shadow models | Shadow state | Low |

**Error isolation:** Steps 2–12 wrapped in try/except (log and continue); steps 13–14 separate try blocks.

---

## 2. Vehicle Integration Supervisor

| Property | Value |
|----------|-------|
| **File** | `energy_core/vehicles/supervisor.py` |
| **Start** | `Collector.setup()` → `await self._vehicle_supervisor.start()` |
| **Model** | Per-site asyncio task |
| **REST refresh** | Every 300s (`REST_REFRESH_SECONDS`) |
| **Adaptive poll** | `vehicles/polling.py` — interval varies by charging/plugged state |
| **Transport** | Mercedes WebSocket (`websocket_client.py`) |
| **Backoff** | 900s on auth failure; circuit breaker after 5 failures |

**Data:** `vehicle_state_latest`, `vehicle_state_history`, `vehicle_attribute_observations`

---

## 3. Solar Forecast Coordinator

| Property | Value |
|----------|-------|
| **File** | `energy_core/solar_forecast/coordinator.py` |
| **Trigger** | `run_due_sites()` each collector cycle |
| **Refresh interval** | `SOLAR_FORECAST_REFRESH_MINUTES` (default 30) |
| **Retention prune** | 14 days |
| **External calls** | Open-Meteo, SMHI, DMI |

**Also runs:** Observation evaluation (moved off HTTP GET per Performance v2)

---

## 4. Arctic Spa Polling

| Property | Value |
|----------|-------|
| **File** | `integrations/arctic_spa/polling.py` |
| **Interval** | 60s default; 15s during active cleaning |
| **Gate** | `ARCTIC_SPA_ENABLED=false` by default |
| **Due-time** | Per-consumer polling in collector spa integration |

---

## 5. Smart Charging Engine

| Property | Value |
|----------|-------|
| **File** | `energy_core/charging/engine.py` |
| **Trigger** | Every collector cycle (separate DB session) |
| **Action** | Charge Amps current control based on `EnergyState` |
| **Output** | `ev_bridge_cycles`, charger state updates |

---

## 6. Backend Lifespan (NOT background jobs)

`backend/app/main.py` lifespan:
- DB engine init
- Snapshot cache config
- SQL tracking install
- **No background tasks started**

---

## 7. Frontend Timers (client-side, not server jobs)

| Timer | Interval | File |
|-------|----------|------|
| SiteDataProvider | 30s | `SiteDataProvider.tsx` |
| Pi dashboard | 4s | `usePiDashboardData.ts` |
| Performance page | 10s | `system/performance/page.tsx` |
| Various dashboard hooks | 30–60s | `use*DashboardData.ts` |

These are **client polls**, not background workers — but they drive server load.

---

## 8. Job Collision Analysis

| Collision | Risk | Mitigation |
|-----------|------|------------|
| Collector poll overlaps next poll | **MEDIUM** | If cycle > interval, polls stack (single loop prevents parallel) |
| Smart charging + virtual bridge same cycle | LOW | Separate sessions |
| Solar refresh + weather fetch during slow Heartbeat | MEDIUM | Sequential — total cycle extends |
| Vehicle supervisor + collector both hit DB | LOW | Async concurrent sessions |
| Multiple sites price refresh sequential | MEDIUM | No parallel limit |

**Double-start risk:** Single collector container — no distributed locking needed for single-instance deploy. **Multi-collector would duplicate work** — no leader election (UNKNOWN if multi-collector ever deployed).

---

## 9. Work That Should Move to Background (already done vs remaining)

| Work | Current location | Status |
|------|------------------|--------|
| Heartbeat readings ingest | Collector | ✅ Done |
| Price engine refresh | Collector | ✅ Done |
| Solar forecast evaluation | Collector | ✅ Done (v2) |
| Spa interval rebuild | Collector | ✅ Done (v2) |
| Snapshot writing | Collector | ✅ Done |
| Smart charging control | Collector | ✅ Done |
| Financial stats computation | **HTTP GET** | ❌ Should precompute in collector |
| Solar forecast GET assembly | **HTTP GET** (heavy) | ❌ Should serve snapshot |
| Display overview aggregation | **HTTP GET** | ⚠️ Partial cache (3s) |

---

## 10. Recommended Job Schedule (target state)

| Job | Interval | Priority |
|-----|----------|----------|
| Heartbeat readings | 30s | Critical |
| Live overview prefetch | 30s | Critical |
| Snapshot writer | 30s | Critical |
| Smart charging | 30s | High |
| Price engine | 15 min | High |
| Solar forecast refresh | 30 min | Medium |
| Weather fetch | 45 min | Medium |
| Financial daily rollup | 5 min | Medium |
| Forecast learning | 1 hour | Low |
| Arctic Spa poll | 60s | Low (if enabled) |
| Mercedes vehicle poll | Adaptive 30s–300s | Medium |
| Retention/prune | Daily | Low |

Current implementation runs most jobs **every collector cycle** regardless of due time (except solar coordinator due-check).
