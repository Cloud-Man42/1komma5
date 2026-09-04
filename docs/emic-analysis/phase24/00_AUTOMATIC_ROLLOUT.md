# Phase 24 — AUTOMATIC rollout (Charge Amps)

**Date:** 2026-09-04  
**Site:** `akarp`  
**Prerequisite:** Phase 23 (`ENERGY_CONTROL_PROVIDER=chargeamps`, preview PREVIEW)

---

## Steps

1. Readiness: `.\scripts\phase24-chargeamps-automatic-readiness.ps1`
2. Manual apply + enable AUTOMATIC: `.\scripts\phase24-automatic-activate.ps1`
3. Collector will call `sync_from_strategy` when mode is AUTOMATIC

---

## Readiness checks (Charge Amps path)

| Check | Requirement |
|-------|-------------|
| Mode | `SEMI_AUTOMATIC` or `AUTOMATIC` |
| `control_enabled` | `true` |
| Provider | `chargeamps` |
| Bridge | At least one `bridge_enabled` charger |
| Preview | `USE_NOW` → `PREVIEW` |

Manual apply may return `FAILED` if no vehicle is connected; that does not block AUTOMATIC if preview and bridge are OK.

---

## Rollback

```powershell
# PUT /api/sites/akarp/energy-control/settings
{ "optimization_mode": "SEMI_AUTOMATIC", "control_enabled": true }
```

Smart charging (`SmartChargingEngine`) continues independently.
