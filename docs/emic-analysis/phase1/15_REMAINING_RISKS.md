# Phase 1 — Remaining Risks

**Updated:** 2026-09-04 (post Phase 25)

---

## Production flags (akarp)

| Flag | Prod | Notes |
|------|------|-------|
| `FINANCIAL_AGGREGATES_ENABLED` | **true** | `financial_daily` backfilled |
| `SOLAR_FORECAST_SYNC_REFRESH_ON_READ` | **false** | Keep false in prod |
| `ENERGY_CONTROL_PROVIDER` | **chargeamps** | AUTOMATIC on `akarp` |
| `optimization_mode` | **AUTOMATIC** | Collector applies via Charge Amps |
| `EMIC_ADMIN_TOKEN` | **set** | Admin routes require Bearer on LAN |

---

## Energy control

| Risk | Mitigation |
|------|------------|
| **No Heartbeat-compatible charger** | Class **D** permanent — use Charge Amps path only |
| Heartbeat EV apply | **Deprecated** — `chargeamps` provider is prod path |
| Battery/site EMS writes | Not implemented — Charge Amps EV only |
| Monitor AUTOMATIC | `scripts/phase25-automatic-monitor.ps1` |

---

## Deferred infrastructure

| Item | Risk |
|------|------|
| **Multi-worker** | Per-process L1 cache; Redis L2 shared |
| **Pi cold overview** | ~1.1 s first load; warm p95 240 ms @ 5 users |
| **Auth on LAN** | Admin token when `EMIC_ADMIN_TOKEN` set |

---

## Performance targets

| Route | p95 @ 1 user | Target | Status |
|-------|--------------|--------|--------|
| `dashboard` | **138 ms** | < 250 | OK |
| `solar/forecast` | **7 ms** server-side p95 (167 ms external LAN) | < 100 server | OK (Phase 25) |

---

## Operations

| Area | Status |
|------|--------|
| Timescale retention/compression | **OK** — `phase25-timescale-verify.ps1` |
| Collector slow lane | 15 min — `financial_daily` may lag one interval |

---

## Test suite

- `test-windows.ps1`: **1212 backend + 663+ frontend** (2026-09-04).

---

## Recommended next steps

1. Monitor AUTOMATIC weekly (`phase25-automatic-monitor.ps1`)
2. Battery/site control provider (if product requires)
3. Pi cold-load optimization
4. Product wave 4 — unified optimization dashboard
