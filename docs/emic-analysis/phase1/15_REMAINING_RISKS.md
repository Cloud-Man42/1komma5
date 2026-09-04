# Phase 1 — Remaining Risks

**Updated:** 2026-09-04 (post Phase 21–22)

---

## Production flags (akarp)

| Flag | Prod | Notes |
|------|------|-------|
| `FINANCIAL_AGGREGATES_ENABLED` | **true** | `financial_daily` backfilled; day p95 ~193 ms |
| `SOLAR_FORECAST_SYNC_REFRESH_ON_READ` | **false** | Keep false in prod |
| `ENERGY_CONTROL_PROVIDER` | **heartbeat** | SEMI_AUTOMATIC on `akarp` |
| `EMIC_ADMIN_TOKEN` | **set** | Admin routes require Bearer on LAN |

---

## Energy control

| Risk | Mitigation |
|------|------------|
| **No Heartbeat-compatible charger** | Class **D** is permanent at Åkarp — do not pursue Heartbeat EV registration |
| `ENERGY_CONTROL_PROVIDER=heartbeat` | EV apply always **REJECTED** — use Charge Amps smart charging (`bridge_enabled`) for real control; Phase 23: `chargeamps` provider |
| `write_enabled=false` | Irrelevant until/unless Heartbeat EV path is abandoned or replaced |
| AUTOMATIC via Heartbeat | **Off table** — see [`phase22/00_AUTOMATIC_DECISION.md`](../phase22/00_AUTOMATIC_DECISION.md) |

---

## Deferred infrastructure

| Item | Risk |
|------|------|
| **Multi-worker** | Per-process L1 cache; Redis L2 shared |
| **Pi SSE** | Display still polls ~4 s; cold overview p95 ~1.1 s |
| **Auth on LAN** | Admin token required when `EMIC_ADMIN_TOKEN` set — P0 if network exposure changes |

See [`06_CACHE.md`](06_CACHE.md), [`07_REALTIME.md`](07_REALTIME.md), [`10_SECURITY.md`](10_SECURITY.md).

---

## Pi display

- SSE stream works (GET); benchmark scripts should use GET not HEAD.
- Warm display overview p95 **240 ms** @ 5 users (measured 2026-09-04).
- Phase 2 API fields shipped: solar curve, battery today, price min/max, charger decision, spa filter cycles, vehicle target SoC.

---

## Performance targets still open

| Route | p95 @ 1 user | Target | Status |
|-------|--------------|--------|--------|
| `dashboard` | **138 ms** | < 250 | OK (Phase 22 re-benchmark) |
| `solar/forecast` | **179 ms** | < 100 | FAIL |

---

## Operations

| Area | Risk |
|------|------|
| Timescale retention | Policies documented; verify applied on prod DB |
| Collector slow lane | 15 min interval — `financial_daily` may lag one interval |

---

## Test suite

- `test-windows.ps1`: **1204 backend + 663 frontend** passing (2026-09-04).
- Test `client` fixture isolates `EMIC_ADMIN_TOKEN` from host environment.

---

## Recommended next steps

1. Register EV in Heartbeat app → re-run discovery
2. Enable `write_enabled` after write test
3. Manual apply success → consider AUTOMATIC (`phase22-automatic-readiness.ps1`)
4. Re-benchmark `solar/forecast` if targeting < 100 ms p95
