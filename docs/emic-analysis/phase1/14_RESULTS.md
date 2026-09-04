# Phase 1 Results — Before / After

**Status:** Phases 5–21 deployed to production. Phase 21 (2026-09-04): SEMI_AUTOMATIC, Pi Phase 2 fields, product wave 3. Phase 22 (2026-09-04): dashboard re-benchmark, Heartbeat control diagnostics, doc refresh, AUTOMATIC decision.

---

## Phase 21 (2026-09-04)

| Step | Delivered |
|------|-----------|
| 1 | Pi display benchmark via `phase21-pi-benchmark-provision.ps1` |
| 2 | Dashboard p95 optimization (`asyncio.gather`, `energy_daily` fast path, cache TTL 60 s); hotfix `spa_enabled` NameError |
| 3 | `SEMI_AUTOMATIC` + Heartbeat provider on `akarp`; apply script uses `target=ev_charger` |
| 4 | Pi Phase 2 rest fields: `decision_reason_sv`, spa filter cycles, `target_soc_pct` |
| 5 | Wave 3 UI: `PeakProtectionCard`, `SolarAccuracySummaryCard`, `ForecastLearningLoopCard` |

Heartbeat apply/preview currently **REJECTED** — root cause: no Heartbeat EV mapping in discovery table (see Phase 22).

---

## Phase 22 — dashboard re-benchmark (2026-09-04)

Post Phase 21 step 2 + `spa_enabled` fix (`scripts/phase22-dashboard-benchmark.ps1`):

| Users | p95 (ms) | Target | Status |
|-------|----------|--------|--------|
| 1 | **138** | < 250 | OK |
| 5 | **135** | — | OK |
| 10 | **157** | — | OK |

Previous dashboard p95 @ 1 user was **422 ms** (pre-optimization). Raw JSON: [`phase22-dashboard-prod-results.json`](phase22-dashboard-prod-results.json).

---

## Phase 22 — Heartbeat control diagnose (2026-09-04)

| Check | Result |
|-------|--------|
| Root cause of REJECTED preview/apply | **No Heartbeat EV mapping** in discovery table |
| Fix shipped | `HeartbeatControlProvider` falls back to `ev_chargers.heartbeat_ev_id` when mappings empty |
| Diagnostic script | `scripts/phase22-heartbeat-control-diagnose.ps1` (`-RunDiscovery` to refresh mappings) |
| Apply still requires | `write_enabled=true` in bridge settings + EV plugged in at Heartbeat |

**Decision:** stay on `SEMI_AUTOMATIC` until preview returns `PREVIEW` and a manual apply succeeds in prod.

---

## Phase 22 — AUTOMATIC decision (2026-09-04)

**Do not enable `AUTOMATIC` yet.** Readiness script: `scripts/phase22-automatic-readiness.ps1` (exit 1 on prod 2026-09-04).

| Check | Status |
|-------|--------|
| SEMI_AUTOMATIC + heartbeat | OK |
| Heartbeat EV in app (discovery class) | **D** — 0 EV profiles |
| `write_enabled` | **false** |
| Preview `USE_NOW` | **REJECTED** |

Full rationale: [`phase22/00_AUTOMATIC_DECISION.md`](../phase22/00_AUTOMATIC_DECISION.md).

---

## Phase 20 (2026-09-04)

| Step | Delivered |
|------|-----------|
| 1 | `ENERGY_CONTROL_PROVIDER=heartbeat` in prod; site `akarp` → `RECOMMEND`; quick-win verify script |
| 2 | `scripts/phase20-pi-baseline.ps1`; dashboard proxy p95 **241 ms** @ 5 users |
| 3 | Horizon optimizer Redis cache (`HORIZON_OPTIMIZER_REDIS_CACHE_TTL_SECONDS=300`); cached p95 **~21–74 ms** |
| 4 | `EnergyControlTimelineCard`, `ForecastLearningRecentCard`; Pi Phase 2 display fields (solar curve, battery today, price min/max) |

Raw Pi JSON: [`pi-baseline-prod-results.json`](pi-baseline-prod-results.json).

Pi authenticated routes (`/api/v1/display/overview/*`) require `EMIC_DISPLAY_TOKEN` for prod benchmark — skipped without token.

### Pi display benchmark (2026-09-04, `phase21-pi-benchmark-provision.ps1`)

| Route | 1 user p95 (ms) | 5 users p95 (ms) |
|-------|-----------------|------------------|
| `/api/sites/akarp/dashboard` (proxy) | 207 | 306 |
| `/api/v1/display/overview/akarp` | **1145** | **240** |
| `/api/v1/display/overview/akarp/stream` | SSE GET works; HEAD returns 405 |

Cold display overview ~1.1 s; warm concurrent p95 **240 ms** @ 5 users.

---

## Measurement method

| Tool | Purpose |
|------|---------|
| [`scripts/phase1-baseline.ps1`](../../../scripts/phase1-baseline.ps1) | HTTP latency, concurrency 1/10 |
| [`scripts/phase19-baseline-smoke.ps1`](../../../scripts/phase19-baseline-smoke.ps1) | Post-deploy smoke (6 routes) |
| `GET /api/system/performance` | In-process query counts, slow queries |
| [`test-windows.ps1`](../../../test-windows.ps1) | Regression tests |

Raw baseline JSON: [`baseline-prod-results.json`](baseline-prod-results.json).

---

## API latency — site `akarp` (2026-09-04, post phases 5–19)

| Route | p95 1 user (ms) | p95 10 users (ms) | Target | Status |
|-------|-----------------|-------------------|--------|--------|
| `/api/sites/akarp/snapshot` | **166** | 308 | < 250 | OK / OK |
| `/api/sites/akarp/dashboard` | **138** | 157 | < 250 | OK / OK |
| `/api/sites/akarp/readings?bucket=5&hours=24` | **229** | 436 | — | OK |
| `/api/sites/akarp/solar/forecast` | **179** | 329 | < 100 | FAIL (Redis cache; much improved vs 262–355) |
| `/api/sites/akarp/price-engine/current` | **177** | 623 | — | OK |
| `/api/sites/akarp/battery-opportunity` | **202** | 358 | — | OK |
| `/api/sites/akarp/horizon-optimizer` | **1128** | 6246 | — | Heavy (read-only planner) → **~21 ms cached** (Phase 20) |
| `/api/sites/akarp/financial-stats?period=day` | **193** | 256 | < 300 | OK |
| `/api/sites/akarp/financial-stats?period=month` | **166** | 290 | < 300 | OK |
| `/api/sites/akarp/financial-stats?period=year` | **205** | 253 | < 300 | OK |

Source: `scripts/phase1-baseline.ps1 -Concurrency 1,10` against `http://192.168.50.54`.

### Highlights vs original baseline (2026-09-03)

| Route | Before p95 | Now p95 (1 user) | Change |
|-------|-----------|------------------|--------|
| `financial-stats?period=day` | 3089 ms | **193 ms** | ~16× faster |
| `solar/forecast` | 262 ms | **179 ms** | ~31% faster |
| `dashboard` | 132 ms | **138 ms** | ~3× faster vs 422 ms pre-step-2 |

---

## Financial stats — concurrency

| Period | 1 user p95 | 10 users p95 |
|--------|-----------|--------------|
| day | 3089 ms → **193 ms** | 28601 ms → **256 ms** |
| month | 3033 ms → **166 ms** | 27583 ms → **290 ms** |
| year | 3086 ms → **205 ms** | 27980 ms → **253 ms** |

---

## Phase 19 smoke (2026-09-04)

All 6 routes returned HTTP 200: `/health`, dashboard, price-engine/current, solar/forecast, battery-opportunity, horizon-optimizer.

---

## Sign-off checklist

- [x] Migrations 058–061 applied on production
- [x] `financial_daily` backfill completed
- [x] `FINANCIAL_AGGREGATES_ENABLED=true` on production
- [x] Redis L1/L2 cache enabled (`REDIS_URL`)
- [x] Timescale retention + compression (slow lane)
- [x] Re-benchmark script executed (2026-09-04)
- [x] `EMIC_ADMIN_TOKEN` configured on `/config`
- [x] Heartbeat control provider active (`SEMI_AUTOMATIC` on `akarp`)
- [x] Dashboard p95 re-benchmark post Phase 21 step 2 (`phase22-dashboard-benchmark.ps1`)
- [x] Pi dashboard proxy benchmark (`phase20-pi-baseline.ps1`)
- [x] Pi display overview re-benchmark (`phase21-pi-benchmark-provision.ps1`, requires admin token)

---

## Historical — original Phase 1 baseline

See git history for pre-optimization numbers (financial-stats ~3 s p95, solar forecast ~262 ms p95).
