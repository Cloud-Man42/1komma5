# Phase 23 — Charge Amps energy control provider

**Date:** 2026-09-04  
**Site:** `akarp`  
**Decision:** Use `ENERGY_CONTROL_PROVIDER=chargeamps` for SEMI_AUTOMATIC/AUTOMATIC EV apply.

---

## What changed

| Item | Detail |
|------|--------|
| Provider | `ChargeAmpsControlProvider` maps `USE_NOW` → `QUICK_CHARGE`, `WAIT` → `PAUSED` |
| Apply path | Updates `ev_chargers.charging_mode` + `ChargingCommandController` via Charge Amps API |
| Prod default | `ENERGY_CONTROL_PROVIDER=chargeamps` (replaces `heartbeat` for EV control) |

---

## Hardware (unchanged)

- Charge Amps Halo: real charger control (`bridge_enabled`)
- Mercedes EQE: telemetry only (Mercedes API)
- Heartbeat EMS: energy/prices — **not** EV PATCH path

---

## Rollout

```powershell
.\scripts\phase23-chargeamps-control-activate.ps1
```

Preview first (dry-run via API), then apply `USE_NOW` / `WAIT` on `ev_charger` target.

Rollback: set `ENERGY_CONTROL_PROVIDER=noop` or `optimization_mode=RECOMMEND`.
