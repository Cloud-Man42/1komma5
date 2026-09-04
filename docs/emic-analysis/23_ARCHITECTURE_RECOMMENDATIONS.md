# EMIC Architecture Recommendations

Based on verified codebase state (post Performance v2, migration 057).

---

## 1. Current vs Target Architecture

### Current (verified)
```
External APIs → Collector (monolith loop) → PostgreSQL
                    ↓
              site_live_snapshots
                    ↓
              FastAPI (158 endpoints) ← HTTP poll ← Next.js clients (N×)
```

### Target
```
External APIs / Devices
         ↓
   Data Collectors (prioritized sub-loops)
         ↓
   Normalization Layer (Unified EnergyState)
         ↓
   Energy State Engine (single builder)
         ↓
   Time-Series Storage (TimescaleDB + retention)
         ↓
   Cache / Snapshot / State (Redis + DB)
         ↓
   Optimization / Decision Engine
         ↓
   API / SSE / WebSocket
         ↓
   Dashboard / Kiosk / Widgets
```

---

## 2. Key Recommendations

### R1: Unified EnergyState Builder (Priority: HIGH)
**Problem:** 5 parallel models (readings, EnergyState, EnergySiteSnapshot, dashboard JSON, display JSON)  
**Action:** Single `EnergyStateBuilder` in energy-core producing canonical snapshot consumed by dashboard, display, widget, SSE  
**Files to consolidate:** `snapshots/writer.py`, `dashboard.py`, `display_service.py`, `energy_state/service.py`

### R2: Redis Shared Cache + Pub/Sub (Priority: HIGH)
**Problem:** Process-local L1; SSE polls DB every 1s  
**Action:** Redis for snapshot cache + pub/sub on collector write → SSE push  
**Trigger:** When deploying multiple uvicorn workers

### R3: Collector Task Prioritization (Priority: HIGH)
**Problem:** 15 sequential steps per cycle; solar weather can delay snapshots  
**Action:** Split into:
- Critical loop (30s): readings, overview, snapshot, smart charging
- Medium loop (5 min): prices, aggregation, financial rollup
- Slow loop (30 min): solar refresh, forecast learning

### R4: Pre-computed Read Models (Priority: HIGH)
**Problem:** Heavy GET paths (financial stats, solar forecast)  
**Action:** Collector writes `daily_financial_stats`, `solar_forecast_snapshot` tables; GET is pure read

### R5: Client Push Model (Priority: MEDIUM)
**Problem:** N clients × M polls  
**Action:** Wire dashboards to existing SSE `/live-stream`; fallback to poll  
**Files:** `useSiteDashboard.ts`, `SiteDataProvider.tsx`, `snapshot.py`

### R6: Price Store Unification (Priority: MEDIUM)
**Problem:** Dual `market_prices` + `price_periods`  
**Action:** Migrate `list_financial_stats` to `price_periods`; deprecate hourly store

### R7: API Authentication Layer (Priority: MEDIUM)
**Problem:** Open admin API  
**Action:** Optional API key middleware for write endpoints; keep read open on LAN if desired

### R8: Timescale Lifecycle (Priority: MEDIUM)
**Problem:** Unbounded raw data growth  
**Action:** Retention policies: raw 90d, CAGG 5y, compression after 7d

### R9: Observability Stack (Priority: MEDIUM)
**Action:** Prometheus metrics exporter + structured JSON logs + integration health endpoint

### R10: Domain Repository Split (Priority: LOW)
**Problem:** `repositories.py` too large  
**Action:** Split by aggregate without changing API contracts

---

## 3. Migration Path (Phased)

### Phase A — Quick (1–2 sprints)
1. Fix frontend polling duplication
2. Solar forecast snapshot GET
3. Daily financial pre-aggregation
4. Integration health endpoint

### Phase B — Foundation (1–2 months)
1. Unified EnergyStateBuilder
2. Redis cache
3. SSE for main dashboards
4. Collector task split

### Phase C — EMS (3–6 months)
1. Battery Opportunity Engine
2. Closed-loop forecast learning
3. Unified horizon optimizer
4. Heartbeat battery actuation (if API supports)

---

## 4. What NOT to Change

- Keep collector as single ingestion point (works well post v2)
- Keep energy-core as domain monolith (cohesive)
- Keep SQLite for dev/test
- Keep Charge Amps/Mercedes/spa integration patterns (resilience is good)
- Keep Pi Caddy token injection pattern (secure)

---

## 5. Technology Additions (when justified)

| Technology | When | Why |
|------------|------|-----|
| Redis | Multi-worker or SSE push | Shared cache + pub/sub |
| Prometheus | Production ops | Metrics |
| WebSocket | After SSE proven | Bi-directional control |
| Separate read replica | High read load | Scale dashboards |

**Do not add prematurely:** Kubernetes, microservices split, separate TSDB.

---

## 6. Architecture Decision Records Needed

1. Auth model for internet-exposed deployments
2. Raw data retention period
3. Single vs multi-collector with leader election
4. Battery control authority (EMIC vs Heartbeat vs inverter)

---

## 7. Alignment with "Extreme EMIC"

Target architecture directly enables:
- Prediction (forecast learning loop)
- Optimization (horizon optimizer on unified state)
- Automation (energy_control apply)
- Learning (correction EMA + ML retrain)
- Arbitrage (battery opportunity engine on price_periods)

See `27_EXTREME_EMIC.md`.
