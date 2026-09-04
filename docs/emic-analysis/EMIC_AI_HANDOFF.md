# EMIC AI Handoff — Architecture & Product Brief

**Purpose:** Enable a senior AI/system architect with zero prior EMIC context to perform qualified architecture and product analysis.  
**Date:** 2026-09-03  
**Repo:** `1komma5`  
**Rule:** All claims below are from code inspection. Secrets are never included.

---

## 1. What EMIC Is

EMIC (Energy Monitoring In a Cloud) monitors and partially manages residential energy systems in Sweden. It tracks solar production, house consumption, grid import/export, battery state, EV charging (Charge Amps Halo), optional Mercedes vehicles, optional Arctic Spa, and computes economics ( savings, export revenue, net cost). Deployment is Docker-based with Caddy TLS reverse proxy.

**Not a full EMS today** — strongest in monitoring + EV smart charging; battery/HVAC actuation is mostly absent.

---

## 2. Architecture (Concrete)

```
Clients: Next.js browser, Pi Chromium kiosk, Apple widget, Windows tray
    ↓ HTTPS
Caddy (:443) → /api/* → FastAPI backend (:8000)
             → /*     → Next.js frontend (:3000)
    ↓
FastAPI (thin, 158 endpoints) → packages/energy-core (domain logic)
    ↓
PostgreSQL 16 + TimescaleDB (prod) / SQLite (dev)
    ↑ writes
Collector (asyncio poll loop, 30-60s) → Heartbeat, Charge Amps, Mercedes WS, Arctic Spa, weather APIs
```

**Key architectural decision (Performance v2):** Dashboard GET reads DB snapshots — no live Heartbeat on page load. Collector prefetches one live overview per site per cycle.

---

## 3. Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 async, Pydantic |
| Domain | `packages/energy-core` (~433 py files, 30+ packages) |
| Collector | Python asyncio, `collector/app/collector.py` |
| Frontend | Next.js 15, React 19, TypeScript, Recharts, Vitest |
| DB prod | PostgreSQL 16 + TimescaleDB (`ENABLE_TIMESCALEDB=true`) |
| DB dev | SQLite `energy-dev.db` |
| Proxy | Caddy 2 |
| Migrations | Alembic, head `057_energy_control_interface` |
| Tests | ~1110 pytest + ~110 frontend vitest files |
| Package mgr | uv workspace |

---

## 4. Database

**~60 tables** in `packages/energy-core/src/energy_core/db/models.py`

Critical tables:
- `energy_readings` — site power time-series (PK: site_id + recorded_at)
- `price_periods` — 15-min prices (canonical for price engine)
- `market_prices` — hourly legacy (still used by financial stats)
- `site_live_snapshots` — precomputed dashboard JSON
- `ev_chargers`, `ev_charging_sessions` — EV accounting
- `vehicle_*` — Mercedes integration
- `consumer_*`, `spa_*` — Arctic Spa
- `solar_forecast_*`, `solar_*` — solar pipeline (15+ tables)
- `energy_forecast_snapshots` — forecast learning
- `energy_control_actions` — automation log

Timescale hypertables: `energy_readings`, `consumer_samples`, `vehicle_state_history`  
CAGG: `energy_readings_5min`, `energy_readings_1hour`  
**No raw data retention policy** — risk at 3-5 years.

---

## 5. Data Flows

### Ingestion (collector every 30-60s)
1. Heartbeat readings → normalize → upsert `energy_readings`
2. Price engine refresh → `price_periods`
3. Live overview prefetch (1×/site) → used by EV accounting, balance
4. Arctic Spa poll (if enabled)
5. EV accounting, vehicle sessions, energy balance
6. Solar forecast refresh (due sites, ~30 min)
7. Forecast learning sync
8. Energy control sync (non-MONITOR_ONLY sites)
9. Hourly/daily rollups
10. Snapshot writer → `site_live_snapshots`
11. Smart charging → Charge Amps control
12. Virtual Heartbeat bridge + EMS shadow

### Dashboard load (browser)
1. `SiteDataProvider` polls `GET /api/sites/{slug}/dashboard` every 30s
2. Page hooks poll additional endpoints (solar, history, EV, etc.)
3. All fetches use `cache: "no-store"`
4. Pi kiosk: single `GET /api/v1/display/overview/{slug}` every 4s

---

## 6. Integrations

| Integration | Status | Protocol | Auth |
|-------------|--------|----------|------|
| 1Komma5 Heartbeat | Active | HTTPS REST | JWT (encrypted in DB) |
| Sungrow | Via Heartbeat | — | — |
| Charge Amps | Active | HTTPS REST v5 | API key + credentials |
| Mercedes | Active | WebSocket + REST | OAuth (encrypted in DB) |
| Arctic Spa | Optional | HTTPS REST | X-API-KEY |
| ChargeFinder | Active | Web scrape | AES key from web app |
| SMHI/DMI/Open-Meteo | Active | HTTPS open data | None/public |
| Nord Pool | **Not direct** | Prices via Heartbeat | — |
| Modbus | **Removed** | — | — |
| Sensibo, Stripe, eBEcon | **Not in code** | — | — |

Resilience: `providers/resilience.py` — CircuitBreaker (3 failures, 60s cooldown) + LastKnownGoodStore.

---

## 7. Background Jobs

All in collector — no Celery. See `07_BACKGROUND_JOBS.md`.

Vehicle supervisor: separate asyncio tasks per site (`vehicles/supervisor.py`).

---

## 8. Real-Time Mechanisms

- **Primary:** Client HTTP polling (4s Pi to 300s sidebar)
- **SSE:** `/api/sites/{slug}/live-stream` — polls DB every 1s (underused by main UI)
- **Mercedes WS:** collector only
- **Recommended:** DEVICE → COLLECTOR → SNAPSHOT → SSE → CLIENT

---

## 9. Energy Model

**Storage:** `energy_readings` columns (W): solar, consumption, grid_import, grid_export, battery_soc, battery_power, ev_power

**Runtime automation:** `EnergyState` dataclass (`energy/state.py`) — used by smart charging

**Widget/display:** `EnergySiteSnapshot` (`energy_state/models.py`)

**Dashboard:** `DashboardResponse` assembled in `backend/app/api/dashboard.py` and `snapshots/writer.py`

**Gap:** No single unified model for all consumers. Energy balance (`energy_balance/engine.py`) validates Sungrow vs Heartbeat vs Halo but only for diagnostics.

---

## 10. Economics Model

Implementation: `EnergyReadingRepository.list_financial_stats()` in `db/repositories.py`  
Docs: `docs/ekonomi-berakning.md`

- Purchase price: hourly `market_prices.all_in_price_eur_kwh` → SEK, fallback site config
- Solar direct + battery discharge savings at purchase price
- Export revenue: spot + adjustments via `export_revenue/calculator.py`
- Tax credit (skattereduktion): 0 from 2026-01-01
- Net cost = import cost − export revenue

**Issue:** Computes in Python from all raw readings — slow. Dual price granularity (hourly vs 15-min).

---

## 11. Battery Logic

- Monitored via readings (SOC, power) — **not controlled by EMIC**
- `battery_energy_ledger` tracks solar vs grid sourced battery energy for EV attribution
- Smart charging considers battery SOC/power for EV decisions only
- No Battery Opportunity Engine yet — data exists (prices, forecast, SOC)

---

## 12. EV Logic

**Best-automated subsystem.**

Files: `charging/engine.py`, `optimizer.py`, `smart_schedule.py`  
Modes: PAUSED, QUICK_CHARGE, PRICE_CHARGE, SOLAR_CHARGE, SMART_CHARGE  
Control: Charge Amps current writes each collector cycle  
Inputs: `EnergyState` (prices, PV, grid, battery, EV, vehicle SOC/deadline)  
UI: `/sites/{slug}/ev`, energy reasoning panel, solar charging plan API

---

## 13. Forecasting

| Type | Implementation | Accuracy tracking |
|------|----------------|-------------------|
| Solar | `solar_forecast/` + `solar_intelligence/` | `/solar/accuracy`, correction EMA |
| Load | `flexible_load/house_load.py` (14-day profile) | forecast_learning kind `load_w` |
| Price | Stored actuals, not predicted | forecast_learning kind `import_price_sek_kwh` |
| EV | Smart schedule from prices + solar plan | — |

Forecast learning records predict vs actual but **does not auto-tune** (yet).

---

## 14. UI

Routes under `frontend/src/app/`:
- `/sites/[slug]` — overview
- `/sites/[slug]/energy`, `/solar`, `/ev`, `/costs`, `/vehicle`, `/spa`, `/diagnostics`
- `/display/[slug]` — Pi kiosk
- `/config` — settings

Nav: `components/intelligence-dashboard/navItems.ts`  
Polling: fragmented — see `02_APPLICATION_FLOW.md`  
UX gap: 3-second comprehension mostly met on overview/Pi; price/optimization status secondary

---

## 15. Raspberry Pi

- Pi 3, Chromium kiosk, labwc/Wayland
- Local Caddy injects display token for `/api/*`
- Polls display overview every 4s
- Phase 2 fields not yet in display API (forecast curve, battery today, etc.)
- No persistent offline LKG

Docs: `docs/PI_KIOSK.md`, `scripts/pi/kiosk/`

---

## 16. Performance Problems

| Issue | Severity | p95 evidence |
|-------|----------|--------------|
| Solar forecast GET under concurrency | CRITICAL | 34s @ 10 users |
| Financial stats Python integration | HIGH | — |
| SSE 1s DB poll | HIGH | — |
| Duplicate dashboard polls | MEDIUM | — |
| Pi 4s over-polling | MEDIUM | — |
| No Timescale retention | MEDIUM | — |

Baseline: `docs/performance/REPORT.md`, script `scripts/performance-baseline.ps1`

---

## 17. Reliability Problems

- Heartbeat outage → stale but non-crashing (conditional upsert, skip degraded)
- No bulkhead isolation in collector — slow solar blocks snapshot
- Multi-worker L1 cache miss
- DB connection risk under many SSE clients + polls

Circuit breakers: Heartbeat, ChargeFinder. Mercedes auth backoff 900s.

---

## 18. Security Observations

- **Main API unauthenticated** — HIGH risk if beyond LAN
- Widget/display: token auth OK
- Apple device admin: no auth
- Secrets: Fernet encrypted in DB; Pi token in `/etc/emic/kiosk.env`
- CORS: localhost dev only
- Credentials not exposed in frontend API responses (verify response schemas)

---

## 19. Technical Debt (Top 5)

1. Open admin API
2. Dual price stores
3. Fragmented energy model (5 representations)
4. `repositories.py` god class
5. Solar forecast GET not snapshotted

Full list: `24_TECHNICAL_DEBT.md` (30 items)

---

## 20. Existing Features

- Multi-dashboard web UI with hash sub-navigation
- Pi touch kiosk with section detail views
- Apple + Windows widgets
- Smart EV charging with Charge Amps
- SPA smart control (Arctic Spa) with shadow mode
- Mercedes vehicle integration
- Solar forecast (physical + ML intelligence)
- Price engine with green/normal/red tiers
- Energy strategy + energy control (early)
- Forecast learning recording
- Heartbeat virtual bridge / virtual EVSE
- ChargeFinder away charging lookup
- Performance center UI
- SEMP protocol endpoints
- Economics with export revenue + tax credit handling

---

## 21. Planned / Partial Features

- Energy control apply (preview exists, automation early)
- EMS shadow simulation (runs in collector, no UI)
- Energy orchestration priorities (config only)
- Pi Phase 2 display fields (documented, not in API)
- Solar intelligence auto-train (manual trigger)
- Redis cache (deferred in performance report)
- Forecast learning → auto-tune (recording only)

---

## 22. Top Optimization Opportunities

1. Solar forecast collector snapshot
2. Pre-aggregated daily financial stats
3. Redis shared cache + SSE pub/sub
4. Unified frontend polling / SSE subscription
5. Timescale retention + compression
6. Collector task prioritization
7. Display overview from snapshot only

Full list: `25_PERFORMANCE_OPPORTUNITIES.md`

---

## 23. Top New Feature Opportunities

1. Integration health overview strip
2. Battery Opportunity Advisor (read-only)
3. Best EV charge window card on overview
4. Closed-loop forecast learning
5. Unified horizon optimizer (EV + spa + battery)
6. Pi offline LKG + Phase 2 fields
7. Peak demand / effekttariff alerts
8. Load disaggregation (house - EV - spa)

Full list: `26_PRODUCT_OPPORTUNITIES.md`, `22_FEATURE_IDEAS.md`

---

## 24. Open Questions (UNKNOWN)

- Heartbeat API battery write capabilities at production sites
- Production MAPE values for solar forecast
- Whether EMIC is exposed beyond LAN
- Multi-collector deployment plans
- Production concurrent user count
- eBEcon integration intent
- Installed battery capacity per site (display defaults 13.5 kWh)
- Whether SSE is used by production browser dashboards
- Code coverage percentage (not in CI)

---

## 25. Important File Paths

### Entry points
- `backend/app/main.py` — FastAPI app, router registration
- `collector/app/collector.py` — poll loop
- `frontend/src/lib/api.ts` — all frontend API calls
- `packages/energy-core/src/energy_core/config.py` — settings

### Domain core
- `packages/energy-core/src/energy_core/db/models.py` — ORM
- `packages/energy-core/src/energy_core/db/repositories.py` — readings, financial stats
- `packages/energy-core/src/energy_core/energy/state.py` — EnergyState
- `packages/energy-core/src/energy_core/charging/engine.py` — smart charging
- `packages/energy-core/src/energy_core/price_engine/` — 15-min prices
- `packages/energy-core/src/energy_core/snapshots/writer.py` — snapshot builder
- `packages/energy-core/src/energy_core/providers/resilience.py` — circuit breaker

### API layer
- `backend/app/api/dashboard.py` — main dashboard
- `backend/app/api/snapshot.py` — snapshot + SSE
- `backend/app/display_service.py` — Pi overview
- `backend/app/api/solar_forecast.py` — solar (perf critical)

### Frontend
- `frontend/src/lib/SiteDataProvider.tsx` — shared dashboard state
- `frontend/src/lib/usePiDashboardData.ts` — Pi polling
- `frontend/src/components/intelligence-dashboard/navItems.ts` — navigation

### Infrastructure
- `docker-compose.yml` — production stack
- `Caddyfile` — routing
- `alembic/versions/` — migrations
- `docs/performance/REPORT.md` — perf baseline
- `docs/ekonomi-berakning.md` — economics spec
- `docs/PI_KIOSK.md` — kiosk docs

### Analysis output
- `docs/emic-analysis/` — full 28-document analysis suite
- `docs/emic-analysis/EMIC_ANALYSIS.json` — machine-readable index

---

## 26. Suggested Analysis Prompt for External AI

> Given this handoff and the full `docs/emic-analysis/` corpus, propose a 12-month roadmap to transform EMIC from an energy monitor into an advanced home EMS. Prioritize: (1) solar forecast scalability, (2) unified EnergyState, (3) battery arbitrage advisory, (4) client push architecture, (5) security hardening for potential internet exposure. Ground all recommendations in the existing energy-core modules — do not propose greenfield rewrite.

---

## 27. Document Index

Read in order for full depth: `00` → `27`, or by topic from filenames. JSON index: `EMIC_ANALYSIS.json`.
