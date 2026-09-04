# Phase 22 — AUTOMATIC mode decision

**Date:** 2026-09-04 (updated)  
**Site:** `akarp`  
**Decision:** **Do not enable `AUTOMATIC` via Heartbeat EV control.** Heartbeat EV registration is **not available** on this site.

---

## Hardware constraint (Åkarp)

| Component | Status |
|-----------|--------|
| Charge Amps Halo | ✅ Physical charger — smart charging via EMIC collector |
| Mercedes EQE | ✅ Telemetry via Mercedes API (not Heartbeat EV profile) |
| Heartbeat EMS | ✅ Energy / Sungrow / prices |
| Heartbeat EV profile | ❌ **Not possible** — no Heartbeat-compatible charger pairing |

Discovery class **D** (`EV_ID_NOT_FOUND`) is expected and **cannot be fixed** by registering EQE in the Heartbeat app.

**Real control path today:** `SmartChargingEngine` → Charge Amps API (`bridge_enabled` on charger).  
**Not applicable:** `HeartbeatControlProvider` PATCH on Heartbeat EV devices.

---

## Current prod settings

| Setting | Value | Note |
|---------|-------|------|
| `optimization_mode` | `AUTOMATIC` | Collector applies strategy via Charge Amps |
| `ENERGY_CONTROL_PROVIDER` | `chargeamps` | EV apply via Charge Amps Halo bridge |
| Smart charging bridge | Charge Amps | Same physical path as energy_control provider |

---

## Revised roadmap (no Heartbeat EV)

1. **Keep smart charging** on existing Charge Amps bridge (collector `SmartChargingEngine`).
2. **Phase 23 (done):** `ENERGY_CONTROL_PROVIDER=chargeamps` — map `USE_NOW`/`WAIT` to Charge Amps `charging_mode` + current writes.
3. **Do not wait** for Heartbeat EV discovery / `write_enabled` / EV watcher scripts.
4. **AUTOMATIC** enabled via Phase 24 — Charge Amps provider + collector `sync_from_strategy`.

---

## Rollout ladder (revised)

```
MONITOR_ONLY → RECOMMEND → SEMI_AUTOMATIC → AUTOMATIC
         ↑ smart charging (Charge Amps) can run in parallel
         ↑ energy_control API timeline = separate concern until chargeamps provider
```

Rollback: set `optimization_mode` to `RECOMMEND` or `MONITOR_ONLY`; smart charging unaffected.

---

## Deprecated automation

Do **not** run:

- `phase22-heartbeat-ev-watcher.ps1`
- `phase22-heartbeat-control-activate.ps1` (Heartbeat EV path)

Use instead:

- `phase22-heartbeat-control-diagnose.ps1` — status only
- EV dashboard + `/config` — Charge Amps bridge settings
