# EMIC Step 2 Final Production Sign-Off

**Date:** 2026-09-07  
**Target:** `http://192.168.50.54`  
**Deploy:** Step 2.5 via `scripts/deploy.local.ps1` (backend + collector + frontend rebuilt)

---

## STEP 2 FINAL PRODUCTION ACCEPTANCE

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Step 2.5 deployed | **PASS** | Docker rebuild; backend/collector/frontend recreated |
| Correct version running | **PASS** | Auth 401, legacy filter, orchestrator logs present (pre-2.5 lacked these) |
| Post-deploy health | **PASS** | `verify-prod-health.ps1` all OK (×3 runs) |
| Module PUT authentication | **PASS** | PUT without Bearer → 401 |
| Legacy aliases filtered | **PASS** | Site module list: 11 modules (was 17 with legacy aliases) |
| Orchestrator active | **PASS** | Collector logs: `ModuleStartRequested`, `ModuleStarted`, `WorkerStarted` |
| Redis event lifecycle | **PASS** | PUT enable/disable → collector logs start/stop within seconds |
| Denmark runtime cycle | **PASS** | site_id=2 solar-forecast: Start→Stop→Start→Stop via PUT + logs |
| Runtime state real | **PARTIAL** | Collector registry authoritative; **API `runtime_status` reads backend process registry (always stopped/blocked)** |
| Disable stops work | **PASS** | `ModuleStopRequested`, `CapabilityUnregistered` in collector logs |
| Capabilities removed on stop | **PASS** | `CapabilityUnregistered site_id=2 module_id=feature.solar-forecast` |
| Re-enable restores capabilities | **PASS** | `CapabilityRegistered` after enable |
| No duplicate workers | **PASS** | Idempotent enable cycles; single Start/Stop pair per transition |
| Charge Amps acceptance | **SAFELY DEFERRED** | 409 guards: cannot disable smart-charging (energy-balance dep) or chargeamps (smart-charging dep) without full dependency chain; Halo WAITING_TO_START / no vehicle |
| Smart Charging recovery | **SAFELY DEFERRED** | Same dependency chain; collector logs show chargeamps+smart-charging RUNNING after startup sync |
| Site isolation | **PASS** | Denmark toggles did not change akarp module enabled flags |
| Persistence | **PASS** | DK solar disabled in DB; collector restart → no site_id=2 ModuleStart in startup logs |
| Regression tests | **PASS** | 1380 Python tests pre-deploy |
| Performance | **PASS** | Pre/post baseline comparable; snapshot ~106ms, dashboard ~97ms @1 user |
| Final health | **PASS** | Post-acceptance `verify-prod-health.ps1` all OK |

---

## Pre vs Post Deploy

| Check | Pre-deploy | Post-deploy |
|-------|------------|-------------|
| Health | All OK | All OK |
| Module count (API) | 17 (with legacy) | 11 (canonical only) |
| PUT without auth | 200 | **401** |
| Orchestrator in collector | No | **Yes** |
| Migration | 062 head | 062 head |

Performance baselines: `docs/performance/baseline-results-pre-step2_5-deploy.json`, `docs/performance/baseline-results-post-step2_5-deploy.json`

---

## Denmark Acceptance Log (site_id=2, feature.solar-forecast)

```
ModuleStartRequested → ModuleStarted → CapabilityRegistered   (enable)
ModuleStopRequested → ModuleStopped → CapabilityUnregistered  (disable)
```

Repeated twice via authenticated PUT. Restored to `enabled=false`.

---

## Redis Event Path

Verified chain:

```
PUT /api/sites/.../modules/... (Bearer token)
→ SiteModuleService.set_enabled
→ DB site_module_configurations
→ Redis emic:events:modules
→ collector _module_event_listener
→ ModuleOrchestrator.start_module / stop_module
```

Manual `publish_module_state_change` from backend container: `publish_ok=True`, collector reacted.

---

## Charge Amps (akarp) — Deferred Rationale

Attempted disable per acceptance plan:

- `PUT disable feature.smart-charging` → **409** (`feature.energy-balance` dependent)
- `PUT disable integration.chargeamps` → **409** (`feature.smart-charging` dependent)

Dependency guards work correctly. Full disable chain would require disabling energy-balance → smart-charging → chargeamps in maintenance window. Halo state `WAITING_TO_START`, no vehicle connected — low active charging risk, but 409 guards prevent partial unsafe disable.

Collector startup logs confirm akarp chargeamps + smart-charging reach RUNNING with capability registration.

---

## Findings by Severity

### HIGH

| ID | Finding |
|----|---------|
| H1 | **API `runtime_status` does not reflect collector `ModuleRuntimeRegistry`** — backend and collector are separate processes; GET modules shows `stopped`/`blocked` while collector orchestrator has modules RUNNING. Enable/disable **does** affect collector runtime via Redis. |

### MEDIUM

| ID | Finding |
|----|---------|
| M1 | Fast-lane log line `bridge_count` can be `None` when `_run_lane` returns void — causes logging `TypeError` (non-fatal) |
| M2 | Akarp smart-charging shows `runtime_status=blocked` in API while collector started it successfully at startup |

### LOW

| ID | Finding |
|----|---------|
| L1 | SMHI SNOW 404 warnings on solar intelligence (pre-existing, non-blocking) |

### INFO

| ID | Finding |
|----|---------|
| I1 | Redis fallback `mark_site_modules_dirty` is in-process only on backend; cross-process fallback relies on lane `sync_dirty` in collector (empty unless collector marks dirty) — Redis is primary path |

---

## Blockers for Step 3

**None.** Runtime lifecycle works in collector; disable stops work; auth enforced; no health/perf regression.

H1 should be addressed early in Step 3 (e.g. persist or pub/sub runtime status for API reads) but does not block integration migrations.

---

## FINAL DECISION

```
GO FOR STEP 3
```

Step 2.5 is deployed and production-verified. Module lifecycle operates end-to-end in the collector via orchestrator + Redis. Remaining debt is API visibility of runtime state (HIGH), not runtime control failure.
