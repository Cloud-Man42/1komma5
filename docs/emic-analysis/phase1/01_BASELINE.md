# Phase 1 Baseline — Measured Before Changes

**Date:** 2026-09-03  
**Target:** Production read-only `http://192.168.50.54`  
**Primary site:** `akarp`

> Note: Phase 0 spec references `BASELINE.md`; this file is `01_BASELINE.md` per the Phase 1 documentation index in `00_PLAN.md`.

## Measurement method

| Source | Script / endpoint | Notes |
|--------|-------------------|-------|
| HTTP latency | [`scripts/phase1-baseline.ps1`](../../scripts/phase1-baseline.ps1) | Concurrency 1/5/10, GET only |
| In-process metrics | `GET /api/system/performance` | Saved to [`baseline-prod-performance.json`](baseline-prod-performance.json) |
| Tests | [`test-windows.ps1`](../../test-windows.ps1) | pytest + dotnet + vitest |
| Build | `npm run build` in `frontend/` | Next.js 15 production build |

Raw benchmark rows: [`baseline-prod-results.json`](baseline-prod-results.json).

---

## Test status

### Backend (pytest)

| Metric | Value |
|--------|-------|
| Collected | 1110 |
| Result | **PASS** (all) |
| Command | `uv run --all-packages pytest` |

### Frontend (Vitest)

| Metric | Value |
|--------|-------|
| Test files | 113 (112 pass, 1 fail) |
| Tests | 620 (619 pass, 1 fail) |
| Failure | `ChargerSetupWizard.test.tsx` — manufacturer select disabled / options not loaded (pre-existing, unrelated to Phase 1) |

### Windows client (dotnet)

| Metric | Value |
|--------|-------|
| Result | **PASS** |

### Full suite (`test-windows.ps1`)

| Result | **FAIL** — blocked by 1 frontend test above |

---

## Build status

| Component | Result | Notes |
|-----------|--------|-------|
| Frontend (`npm run build`) | **PASS** | Compiled with CSS autoprefixer warning (non-blocking) |
| Backend | Not separately measured | No dedicated build step; pytest validates import graph |

---

## API response times (measured)

Site `akarp`, production. Values in milliseconds.

| Route | 1 user avg | 1 user p95 | 5 users p95 | 10 users p95 |
|-------|-----------|-----------|-------------|--------------|
| `/api/sites/akarp/snapshot` | 126.2 | 126.2 | 157.2 | 242.0 |
| `/api/sites/akarp/dashboard` | 132.4 | 132.4 | 611.3 | 171.8 |
| `/api/sites/akarp/readings?bucket=5&hours=24` | 118.1 | 118.1 | 158.1 | 163.3 |
| `/api/sites/akarp/solar/forecast` | 261.6 | 261.6 | 157.7 | 163.5 |
| `/api/sites/akarp/financial-stats?period=day` | 3089.0 | 3089.0 | 14643.6 | 28601.5 |
| `/api/sites/akarp/financial-stats?period=month` | 3033.0 | 3033.0 | 14379.8 | 27583.4 |
| `/api/sites/akarp/financial-stats?period=year` | 3085.9 | 3085.9 | 13930.0 | 27979.5 |
| `/api/sites` | 139.0 | 139.0 | 192.8 | 189.8 |

### Key findings

- **Dashboard / snapshot / readings:** p95 under 250 ms at 1 user; snapshot p95 242 ms at 10 users — within target.
- **Solar forecast:** p95 261 ms at 1 user (fresh cached run); much better than historical ~5 s under stale refresh, but still candidate for dedicated API snapshot.
- **Financial stats:** **Critical bottleneck** — p95 ~3 s at 1 user, ~28 s at 10 users. Primary Phase 3 target.

---

## Dashboard response time

Uses `/api/sites/akarp/dashboard` (see table above).

At 1 concurrent user: **p95 = 132.4 ms** (meets target < 250 ms).

---

## Solar forecast response time

Uses `/api/sites/akarp/solar/forecast`.

At 1 concurrent user: **p95 = 261.6 ms** (above target < 100 ms; snapshot strategy required).

---

## Financial stats response time

Uses `/api/sites/akarp/financial-stats?period=day|month|year`.

| Period | 1 user p95 | 10 users p95 | Target p95 |
|--------|-----------|--------------|------------|
| day | 3089 ms | 28601 ms | 300 ms |
| month | 3033 ms | 27583 ms | 300 ms |
| year | 3086 ms | 27980 ms | 300 ms |

All periods fail target by large margin.

---

## Pi display response time

**UNMEASURED**

Reason: `GET /v1/display/overview/{slug}` requires `display.read` device token ([`backend/app/display_auth.py`](../../backend/app/display_auth.py)). No token available during baseline run.

---

## DB query counts (from `/api/system/performance`)

In-process store (736 requests sampled at measurement time):

| Route (slowest sample) | query_count | db_ms | total_ms |
|------------------------|-------------|-------|----------|
| `/api/sites/akarp/forecast` | 4 | 3242.8 | 5985.4 |
| `/api/sites/akarp/financial-stats` | 3 | 1066.6 | 5973.3 |
| `/api/sites/akarp/ev-chargers/4/energy-reasoning` | 12 | 1435.4 | 3983.3 |

Cache hit rate at measurement time: **0%** (736 misses, 0 hits — cold or single-worker reset).

---

## DB query times (slow queries)

Top slow queries from performance store:

| duration_ms | route | SQL (truncated) |
|-------------|-------|-----------------|
| 2156.8 | `/api/sites/akarp/forecast` | `SELECT market_prices...` |
| 2126.9 | `/api/sites/akarp/financial-stats` | `SELECT market_prices...` |
| 2087.5 | `/api/sites/akarp/forecast` | `SELECT historical_monthly_energy...` |

Financial stats path dominated by full-table reads on `energy_readings` + `market_prices` (see analysis in `04_FINANCIAL_AGGREGATION.md`).

---

## Collector cycle duration

**UNMEASURED**

Reason: No collector task instrumentation exists pre-Phase 1. Will be measured after observability work (migration 060) and reported in `14_RESULTS.md`.

---

## External integration latency

From performance store `providers` array at baseline time: **empty** (no provider metrics accumulated in sampled window).

From `site_snapshots` in same response:

| site | age_seconds | freshness |
|------|-------------|-----------|
| akarp | 10 | LIVE |
| summer-house-denmark | 10 | DEGRADED |

Collector is writing snapshots every ~10 s for akarp.

---

## Memory usage

**UNMEASURED**

Reason: No Docker/SSH access to production host from measurement machine.

---

## CPU usage

**UNMEASURED**

Reason: No Docker/SSH access to production host from measurement machine.

---

## Phase 1 targets (reference)

| Metric | Target p95 | Baseline (1 user) | Status |
|--------|-----------|-------------------|--------|
| Dashboard API | < 250 ms | 132 ms | OK |
| Solar forecast snapshot | < 100 ms | 262 ms | FAIL |
| Pi snapshot | < 100 ms | UNMEASURED | — |
| Financial stats | < 300 ms | 3089 ms | FAIL |
| Live state propagation | < 2 s | ~10 s snapshot age | OK (LIVE) |

---

## Rollback reference

This document captures pre-Phase-1 state. All subsequent changes must be compared against values in [`baseline-prod-results.json`](baseline-prod-results.json) and this file.
