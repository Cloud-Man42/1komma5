# EMIC Step 3 Migration Status

**Last updated:** 2026-09-07

| Integration | Status | Capabilities | Legacy removed | Tests | Notes |
|-------------|--------|--------------|----------------|-------|-------|
| Step 3.0 Runtime status | **DONE** | N/A | N/A | PASS | Redis publish/read, reconcile, bridge_count fix |
| Heartbeat | **DONE** | ENERGY_*, BATTERY_*, PRICE_* | Partial | PASS | engine/reasoning use provider_resolver |
| Price/Nord Pool | **DONE** | PRICE_READ_* | Partial | PASS | provider_resolver added |
| Charge Amps | **PARTIAL** | EV_CHARGER_* | No | PASS | Adapter factory; smart charging decoupled from HeartbeatClient |
| Mercedes | **PARTIAL** | VEHICLE_READ_* | No | PASS | Supervisor lifecycle; factory boundary exists |
| SMHI/DMI/Open-Meteo | **DONE** | WEATHER_READ_* | N/A | PASS | Bootstrap descriptors + capability registration |
| ChargeFinder | **DONE** | READ_STATUS | N/A | PASS | Bootstrap + lane gating |
| Arctic Spa | **ALREADY COMPLIANT** | SPA_* | N/A | PASS | Factory + lane gating pre-existing |
| Sungrow | **PARTIAL** | via Heartbeat | N/A | PASS | Proxied; sungrow types remain in telemetry layer |
| Zaptec/Tesla | **DEFERRED** | — | N/A | PASS | Scaffold only |
| Sensibo/Ebeco/Gecko | **PLANNED** | — | N/A | N/A | Not in codebase |

## Remaining Vendor Leaks

| Location | Severity | Action |
|----------|----------|--------|
| `vehicles/commands/service.py` | MEDIUM | Route all commands through generic vehicle provider |
| `energy_control/heartbeat_provider.py` | LOW | Acceptable wiring layer |
| `charging/readiness.py` chargeamps naming | INFO | Framework readiness helper |

## Step 3.0 Details

- **Publish:** `module_runtime_state.py` from orchestrator transitions
- **Read:** `SiteModuleResolver` merges Redis snapshots
- **Reconcile:** `reconcile_all_sites()` every 120s in collector fast lane
- **Heartbeat refresh:** RUNNING modules refresh Redis TTL each fast lane
