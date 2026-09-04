# EMIC Application Flow

**Source:** Code trace through frontend hooks → `frontend/src/lib/api.ts` → backend routes → energy-core services.

---

## 1. End-to-End Request Flow

```
Browser
  → Next.js page component
  → use*DashboardData hook (or SiteDataProvider)
  → api.ts fetch*() with cache: "no-store"
  → Caddy /api/*
  → FastAPI route handler
  → energy_core repository/service
  → SQLAlchemy async session → PostgreSQL/SQLite
  → (optional) no live external calls on hot GET paths (post Performance v2)
```

**Collector path (parallel, not triggered by UI):**
```
Collector poll loop
  → Heartbeat provider.fetch_readings()
  → normalize → upsert energy_readings
  → enrichment cycle (prices, EV, solar, snapshots)
  → SmartChargingEngine.run_cycle()
```

---

## 2. Global Refresh Configuration

| Mechanism | Interval | Source |
|-----------|----------|--------|
| `useDashboardRefreshSeconds` | From `fetchHeartbeatConfig().dashboard_refresh_seconds`, default **30s** | `frontend/src/lib/useDashboardRefresh.ts` |
| `SiteDataProvider` | **30s** `fetchSiteDashboard` | `frontend/src/lib/SiteDataProvider.tsx`, `sites/[slug]/layout.tsx` |
| Solar layout prefetch | **300s** config + weather | `sites/[slug]/layout.tsx` |
| Sidebar price | **300s** price engine + strategy | `DashboardSidebar.tsx` |

---

## 3. Per-Dashboard Flow

### 3.1 Intelligence Overview (`/sites/[slug]`)

**Page:** `frontend/src/app/sites/[slug]/page.tsx`  
**Hooks:** `useSiteDashboard(slug, 15)`, `useOverviewData`, `SiteDataProvider`

| API Call | Backend | DB / External | Cached |
|----------|---------|---------------|--------|
| `GET /api/sites/{slug}/dashboard` | `dashboard.py` → snapshot/DB | `energy_readings`, `site_live_snapshots`, rollups | SiteDataProvider 30s |
| Same (15s interval on page) | — | — | Duplicate |
| `GET /api/sites/{slug}/solar/config` | `solar_forecast.py` | `solar_site_configurations` | Layout 300s or hook 60s |
| `GET /api/sites/{slug}/readings?bucket=5&hours=24` | `readings.py` | `energy_readings` or CAGG | Hook 60s |
| `GET /api/sites/{slug}/solar/forecast` | `solar_forecast.py` | `solar_forecast_*` tables | Hook 60s |
| `GET /api/sites/{slug}/solar/performance` | `solar_intelligence.py` | `solar_performance_daily` | Hook 60s |
| `GET /api/sites/{slug}/solar/weather` | `solar_forecast.py` | `solar_weather_cache` | Hook 60s |
| `GET /api/sites/{slug}/energy-strategy/current` | `price_engine.py` | `price_periods`, strategy | Card 120s |
| `GET /api/sites/{slug}/forecast-learning/summary` | `forecast_learning.py` | `energy_forecast_snapshots` | Mount only |

**Computed client-side:** production charts, gauge cards, flow summaries from dashboard + history.

**Duplication issues:**
- Dashboard fetched at 15s (page), 30s (layout provider), potentially reused via `useOptionalSiteData`
- Solar config/weather may be fetched in layout (300s) AND overview hook (60s)

---

### 3.2 Energy Dashboard (`/sites/[slug]/energy`)

**Hook:** `useEnergyDashboardData.ts`  
**Sub-sections:** flow, flows, history, live, quality, peaks, reports (`energySection.ts`)

| API | Interval | Backend logic |
|-----|----------|---------------|
| `GET /api/sites/{slug}/dashboard` | 60s (hardcoded, not config) | DB snapshot path |
| `GET /api/sites/{slug}/readings?bucket={bucket}&hours=24` | 60s | CAGG if Timescale else raw |
| `GET /api/sites/{slug}/peaks?period=&year=` | On period change | SQL aggregation |

**Battery:** Derived from dashboard live fields + history — no separate battery API.

**No dedicated Battery route** — battery metrics appear in Energy + Overview + Pi `/display/[slug]/battery`.

---

### 3.3 Solar (`/sites/[slug]/solar`)

**Hook:** `useSolarDashboardData.ts`  
**Sub-sections:** overview, forecast, tomorrow, weather, performance, accuracy

| API | Interval |
|-----|----------|
| `fetchSiteDashboard` | `dashboard_refresh_seconds` |
| `fetchSolarConfig` | config interval |
| `fetchSiteHistory` | config interval |
| `fetchSolarForecast` | config interval |
| `fetchSolarPerformance` | config interval |
| `fetchSolarWeather` | config interval |
| `fetchSolarAccuracy` | config interval |

**Backend:** Heavy solar forecast logic in `solar_forecast/coordinator.py`; evaluation moved to collector (not on GET per Performance v2).

**External (collector only):** Open-Meteo, SMHI, DMI for weather/radiation.

---

### 3.4 Solar Intelligence (`/sites/[slug]/solar/intelligence`)

| API | Interval |
|-----|----------|
| `fetchSolarConfig`, `fetchSolarProviderStatus`, `fetchSolarModelMetrics` | Mount only |
| `fetchSolarAccuracy`, `fetchSolarDiagnostics` | Lazy/debug |

**No polling** — manual refresh only.

---

### 3.5 EV Charging / Charge Amps (`/sites/[slug]/ev`)

**Hook:** `useEvDashboardData.ts`

| API | Purpose |
|-----|---------|
| `GET /api/sites/{slug}/dashboard` | Live EV aggregate |
| `GET /api/sites/{slug}/energy-config` | Site config |
| `GET /api/sites/{slug}/ev-chargers` | Charger list + status |
| `GET .../bridge-status` | Heartbeat bridge |
| `GET .../solar-charging-plan` | Solar plan |
| `GET .../energy-reasoning` | Smart charging decision |
| `GET .../savings` | Session savings |
| `GET .../stats`, `/sessions` | History |
| `GET .../energy-balance/history` | Balance diagnostics |

**Interval:** `dashboard_refresh_seconds` for primary bundle.

**Charge Amps:** No dedicated dashboard — status on `/config` via `fetchChargeAmpsConfig`; live data from ev-chargers endpoints. Control via collector `SmartChargingEngine`.

**Smart Charging:** No dedicated page — reasoning on EV dashboard, config readiness on `/config`, Pi charger panel.

---

### 3.6 Mercedes / Vehicle (`/sites/[slug]/vehicle`)

**Hook:** `useVehicleDashboardData.ts`

| API | Source |
|-----|--------|
| `GET /api/sites/{slug}/vehicles` | DB `vehicles`, `vehicle_state_latest` |
| `GET .../integration/status` | Mercedes supervisor state |
| `GET .../charge-sessions`, `/current` | `vehicle_charge_sessions` |
| `GET .../energy-reasoning` | If charger linked |

**External:** Mercedes WebSocket polled in collector (`VehicleIntegrationSupervisor`), not on page request.

**Admin:** `/admin/integrations/mercedes` — diagnostics, raw attributes, integration actions.

---

### 3.7 Economy (`/sites/[slug]/costs`)

**Hook:** `useEconomyDashboardData.ts`

| API | Interval |
|-----|----------|
| `GET /api/sites/{slug}/dashboard` | Mount only |
| `GET /api/sites/{slug}/financial-stats?period=day` | Mount only |
| `GET /api/sites/{slug}/forecast?year=` | Mount only |
| `GET /api/sites/{slug}/market-prices?hours=24` | Mount only |

**Issue:** Hook exports `refreshSeconds: 60` but **no setInterval** — economy view does not auto-refresh.

**Backend calculation:** `EnergyReadingRepository.list_financial_stats()` — interval integration of readings × hourly prices (`docs/ekonomi-berakning.md`).

---

### 3.8 SPA (`/sites/[slug]/spa`)

**Hook:** `useSpaDashboardData.ts` — polls at `dashboard_refresh_seconds`

| API | Collector vs HTTP |
|-----|-------------------|
| `/spa/status`, `/health` | DB from Arctic Spa poll |
| `/spa/energy/*`, `/history`, `/cost` | `consumer_samples` aggregates |
| `/spa/plan`, `/timeline`, `/events` | Flexible load planner |
| `/spa/economics`, `/shadow` | Cost + shadow mode |
| `/spa/control/config` | Actuator config |

**External:** Arctic Spa API polled in collector (`ArcticSpaPollingService`), not on most GETs (spa interval rebuild removed from HTTP path per Performance v2).

---

### 3.9 Weather

- Solar page `#vader` — `fetchSolarWeather`
- Sidebar — layout prefetch `fetchSolarWeather` every 300s
- Overview `WeatherSolarPanel` — from overview hook 60s
- Pi display — weather section in `display_service.py` (60s cache)

**Source:** Open-Meteo/SMHI via solar forecast pipeline; cached in `solar_weather_cache`.

---

### 3.10 Diagnostics (`/sites/[slug]/diagnostics`)

Multiple panels with mixed intervals:
- `fetchHeartbeatAuditToday` — mount only
- `fetchEnergyControlStatus/Recent` — mount only
- Per-charger `fetchEnergyReasoning`, `fetchVirtualEvseStatus`, `fetchEnergyBalance` — poll `max(refreshSeconds, 15)`

---

### 3.11 Settings / Integrations (`/config`)

| API | Interval |
|-----|----------|
| `GET/PUT /api/system/heartbeat-config` | Mount + save |
| `GET /api/system/chargeamps-config` | Mount |
| `GET /api/system/charging-readiness` | Mount |
| Site CRUD, display enroll, Apple devices | On action |

---

### 3.12 Raspberry Pi Dashboard (`/display/[slug]`)

**Hook:** `usePiDashboardData.ts` — **4s** poll, backoff to 30s on error

| API | Backend |
|-----|---------|
| `GET /api/v1/display/overview/{slug}` | `display_service.py` |

**Auth:** Device token via Pi Caddy proxy (Bearer injected server-side).

**Single aggregated response** — avoids frontend waterfall; backend queries multiple repos internally.

---

### 3.13 Performance Center (`/sites/[slug]/system/performance`)

`GET /api/system/performance` every **10s** — server-side request metrics, cache hit rates.

---

## 4. Dashboard Load Sequence (Typical Overview)

```
t=0ms    Layout mounts SiteDataProvider → fetchSiteDashboard
t=0ms    Page mounts useSiteDashboard(15s) → may duplicate dashboard fetch
t=0ms    useOverviewData → 5 parallel solar/history calls
t=0ms    Sidebar → price engine (if not cached from layout)
t=300s   Layout solar prefetch refresh
t=15-30s Dashboard refresh cycles overlap
```

**Waterfall mitigation (post v2):** `SiteDataProvider` + `useOptionalSiteData` allow child views to reuse dashboard payload.

---

## 5. N+1 and Duplication Findings

| Issue | Severity | Location |
|-------|----------|----------|
| Triple dashboard fetch (15s + 30s + child hooks) | MEDIUM | Overview page + layout |
| Energy dashboard ignores `dashboard_refresh_seconds` (uses 60s) | LOW | `useEnergyDashboardData.ts` |
| Economy no auto-refresh despite exported interval | MEDIUM | `useEconomyDashboardData.ts` |
| Overview + layout both fetch solar config/weather | MEDIUM | layout + `useOverviewData` |
| Pi 4s polling vs 3s display cache | LOW | Over-fetching ~25% |
| SSE 1 DB poll/sec per connected client | HIGH | `snapshot.py` live-stream |
| `list_financial_stats` loads all readings in range to Python | HIGH | `repositories.py:945` |
| Vehicle list endpoints multiple `.all()` queries | MEDIUM | `vehicles.py` |
| display_service multiple repo calls per overview | MEDIUM | `display_service.py` |

---

## 6. Data Freshness by Source

| Data | Freshness | Path |
|------|-----------|------|
| Live power | Collector interval (30–60s) | `energy_readings` latest row |
| Dashboard GET | Snapshot age (collector cycle) | `site_live_snapshots` or L1 cache |
| Market prices | Collector price engine refresh | `price_periods` |
| EV charger status | Collector smart charging + Heartbeat overview | `ev_chargers.last_*` |
| Vehicle SOC | Mercedes supervisor adaptive poll | `vehicle_state_latest` |
| Spa status | 60s Arctic Spa poll | `consumer_samples` |
| Solar forecast | 30 min refresh | `solar_forecast_runs` |
| Weather | 45 min cache | `solar_weather_cache` |

---

## 7. Live vs Cached vs Computed

| View | Live (on GET) | Cached | Computed |
|------|---------------|--------|----------|
| Dashboard | No Heartbeat call | Snapshot L1 + DB | Today totals, live gauges |
| Snapshot | DB read | 5s route cache | — |
| Solar forecast GET | DB + possible compute | Forecast runs | Physical/ML model |
| Financial stats | No | No | Full interval integration in Python |
| Display overview | No external | 3s in-memory | Aggregated sections |
| Energy reasoning | DB | No | Smart charging engine state |
