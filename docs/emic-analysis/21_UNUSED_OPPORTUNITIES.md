# EMIC Unused Data & Opportunities

Functions that could be built from **data EMIC already collects** but does not fully utilize.

---

## 1. Underutilized Data Sources

| Data already collected | Currently used for | Could also power |
|------------------------|-------------------|------------------|
| `energy_forecast_snapshots` (forecast learning) | Summary card (mount only) | Auto-tune forecasts; accuracy dashboard |
| `energy_balance_snapshots` | Diagnostics page only | Overview "data quality" badge; auto-alert |
| `vehicle_halo_correlation` | Vehicle detail page | Smart charging confidence; billing reconciliation |
| `heartbeat_audit` (today/month) | Diagnostics panel | Overview integration health strip |
| `energy_control_actions` | Recent actions in diagnostics | Automation history timeline |
| `price_engine` tomorrow prices | Sidebar (300s) | EV "best charge window" on overview |
| `solar_provider_health` | Intelligence admin | Solar page "weather source" indicator |
| `consumer_aggregates` (spa) | Spa dashboard | House load disaggregation on energy page |
| `battery_energy_ledger` | EV attribution | Battery economics dashboard |
| `ev_bridge_cycles` | Diagnostics/virtual EVSE | Smart charging transparency chart |
| `vehicle_attribute_observations` | Raw attributes admin | Driving pattern insights |
| `charging_station_lookup_cache` | ChargeFinder admin | "Nearby chargers" on vehicle page when away |
| `flexible_load_plan` | Spa plan view | Cross-load optimization view (EV vs spa) |
| `historical_monthly_energy` | Manual historical entry | YoY comparison charts |
| `energy_hourly` / `energy_daily` rollups | Charts (partial) | Instant financial stats without Python loop |
| `site_live_snapshots` JSON | Dashboard GET | SSE push to all clients (infrastructure exists) |
| Mercedes location/charging state | Vehicle dashboard | Geofence-based home charging detection |
| `virtual_charger_decisions` | Bridge admin | EMS decision audit for users |
| Seasonal profiles (`forecasting.py`) | Year forecast only | Monthly budget alerts |
| Peak readings API | Energy peaks section | Demand charge warnings (effekttariff) |

---

## 2. Features Buildable Without New Integrations

### Quick wins (existing data, minimal code)

1. **Integration health strip on overview** — aggregate readiness + audit + snapshot age
2. **"Best time to charge" card** — from `price_engine/tomorrow` already fetched in sidebar
3. **Forecast accuracy on solar overview** — `/solar/accuracy` exists, not on main solar section
4. **Battery source breakdown** — from `battery_energy_ledger` (solar vs grid charged)
5. **Yesterday comparison** — from `energy_daily` rollup
6. **Economy auto-refresh** — hook bug fix, data already fetched

### Medium (existing data, moderate code)

7. **Battery Opportunity Advisor** — price_periods + solar forecast + SOC (read-only)
8. **Load disaggregation estimate** — house - EV - spa from existing readings
9. **Forecast learning dashboard** — `/forecast-learning/recent` not visualized
10. **Energy control timeline** — actions history as user-facing automation log
11. **Pi Phase 2 fields** — extend display_service from existing endpoints
12. **CO₂ savings estimate** — from solar kWh × grid emission factor (config)

### Advanced (existing data, significant code)

13. **Closed-loop forecast tuning** — forecast_learning → correction factor
14. **Unified optimization dashboard** — EV + spa + battery recommendations
15. **Anomaly detection** — sudden consumption spikes from readings history
16. **Export contract ROI tracker** — from export revenue + sell_contract_start_date

---

## 3. Partially Built Features

| Feature | Built | Not connected |
|---------|-------|---------------|
| Energy control | Backend + collector sync | No prominent UI beyond diagnostics |
| EMS shadow simulation | Collector runs it | No user-facing shadow dashboard |
| Energy orchestration | Priority API | Not enforced automatically |
| Solar intelligence ML | Train/backfill API | Manual trigger only |
| ChargeFinder stations | Cached lookups | Not on vehicle "away" flow |
| SEMP protocol | `/semp/*` endpoints | No UI integration |

---

## 4. Data Duplication Without Cross-Use

| Data A | Data B | Opportunity |
|--------|--------|-------------|
| Hourly `market_prices` | 15-min `price_periods` | Unified economics on finer granularity |
| Vehicle charge sessions | EV charger sessions | Unified charging history view |
| Sungrow telemetry | Heartbeat readings | Validated "true production" display |
| Spa consumer samples | House consumption | Spa fraction of total load |

---

## 5. Recommendations

Prioritize connecting **existing API endpoints to overview UI** before adding new integrations. Highest value:
1. Price engine → EV charge window card
2. Forecast learning → accuracy trend
3. Energy balance → data quality indicator
4. Battery ledger → economics breakdown
