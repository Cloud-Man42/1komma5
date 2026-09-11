# EMIC Step 3.5 – Completion & Production Sync

**Date:** 2026-09-07  
**Scope:** Runtime truth, provider decoupling, Redis recovery, production verification (not Step 4)

---

## 1. Objectives

Close Step 3 verification blockers and HIGH/MEDIUM findings before Step 4:

| ID | Issue | Resolution |
|----|-------|------------|
| B1 | Step 3.0 distributed runtime not deployed | Deployed Step 3.0/3.5 to `192.168.50.54` |
| B2 | API/collector runtime divergence | API reads Redis; distributed RUNNING no longer overridden to BLOCKED |
| H1 | Vehicle commands Mercedes-coupled | Generic `IVehicleCommandProvider` + wiring layer |
| H2 | Charging reasoning opens Heartbeat client | `get_active_optimizations()` on energy provider resolver |
| M1 | Stale Redis → synthetic STOPPED | `RuntimeStatus.UNKNOWN` when distributed expected but missing |
| M2 | No Redis recovery test | `test_module_reconcile_recovery.py` |

---

## 2. Runtime State Deployment (B1)

### Code deployed

- `energy_core/cache/module_runtime_state.py` — publish/read/TTL/resolve
- `ModuleOrchestrator._emit_runtime_state()` — Redis publish on transitions
- `SiteModuleResolver` — `read_runtime_states()` + `resolve_distributed_runtime_status()`
- Collector — `refresh_runtime_heartbeats()`, `reconcile_all_sites()` (120s)

### Production verification signals

| Signal | Result |
|--------|--------|
| `module_runtime_state.py` in backend container | **Present** |
| Redis keys `emic:runtime:*` | **Present** (akarp site_id=1, denmark site_id=2) |
| API `/api/sites/akarp/modules` | **running** for collector-owned modules |
| `verify-prod-runtime-consistency.ps1 -Strict` | **PASS** |
| `verify-prod-health.ps1` | **PASS** (pre/post deploy) |

---

## 3. Stale Runtime Semantics (M1)

### Behavior

```text
enabled + Redis configured + no fresh snapshot → UNKNOWN
collector published STOPPED → STOPPED
disabled → STOPPED (unchanged)
no Redis configured → local registry fallback (unchanged)
```

### Implementation

- `RuntimeStatus.UNKNOWN` added to `platform/modules/types.py`
- `resolve_distributed_runtime_status(..., distributed_runtime_expected=True)`
- `SiteModuleResolver` sets `distributed_runtime_expected` when `redis_url` is configured

### Tests

- `test_module_runtime_state.py` — fresh RUNNING/STOPPED/FAILED/BLOCKED/STARTING/STOPPING, missing remote → UNKNOWN
- Legitimate collector STOPPED preserved via snapshot path

---

## 4. API/Collector Consistency (B2)

### Root cause

Backend `SiteModuleResolver` forced `runtime_status=blocked` when local capability projection missed collector-registered capabilities, even when Redis snapshot was `running`.

### Fix

When a distributed snapshot exists, runtime status from Redis is authoritative; local dependency projection no longer overrides RUNNING → BLOCKED.

### Production (akarp, post-fix)

| module_id | API runtime_status |
|-----------|-------------------|
| integration.heartbeat | running |
| integration.chargeamps | running |
| feature.smart-charging | running |
| integration.mercedes | running |

---

## 5. Redis Recovery / Reconciliation (M2)

### Rule

```text
Desired state (DB) vs actual runtime (ModuleRuntimeRegistry)
→ sync_site() / reconcile_all_sites() converges actual → desired
```

### Tests (`test_module_reconcile_recovery.py`)

- DB disable without event → reconcile stops running module
- DB enable without event → reconcile starts stopped module
- Repeated reconcile → idempotent (single worker)

---

## 6. Vehicle Command Abstraction (H1)

### Architecture

```text
VehicleCommandService (vendor-free)
  → providers/vehicle_command_wiring.resolve_vehicle_command_provider()
  → integrations/mercedes/command_provider.MercedesVehicleCommandProvider
  → Mercedes API
```

### Contract

- `IVehicleCommandProvider` — `load_command_features`, `set_target_soc`, `start_charging`, `stop_charging`
- `MockVehicleCommandProvider` for tests
- Generic errors: `VehicleCommandError`, `VehicleCommandsDisabledError`, `VehicleCapabilityUnavailableError`

### Safety preserved

- `commands_enabled` gate
- Per-vehicle capability checks
- Site/vehicle ownership validation

---

## 7. Charging Reasoning Abstraction (H2)

### Architecture

```text
load_energy_reasoning_for_charger()
  → resolve_energy_state_provider()
  → _HeartbeatEnergyProviderAdapter.get_active_optimizations()
  → energy/optimizations.parse_active_optimizations()
```

### Removed from feature layer

- `open_heartbeat_client` in `charging/reasoning.py`
- Duplicate `parse_active_optimizations` (moved to `energy/optimizations.py`)

UI strings may still mention Heartbeat for operator clarity; no vendor imports in reasoning.

---

## 8. Architecture Tests

New guards in `tests/architecture/test_step3_5_guards.py`:

- `vehicles/commands/service.py` must not import Mercedes
- `charging/reasoning.py` must not import Heartbeat client
- Distributed resolver supports UNKNOWN semantics

Existing layering baselines unchanged (no new violations).

---

## 9. Vendor Token Scan (feature files)

| Token | `charging/reasoning.py` | `vehicles/commands/service.py` |
|-------|-------------------------|--------------------------------|
| Heartbeat | UI strings only | — |
| Mercedes | UI strings only | — |
| Sungrow | — | — |
| ChargeAmps | — | — |

Vendor imports confined to `providers/` and `integrations/` wiring layers.

---

## 10. Test Baseline (post Step 3.5)

| Suite | Result |
|-------|--------|
| Python | **1406 passed**, 5 skipped |
| Frontend | **705 passed** |
| Architecture | **33 passed** |

New tests: runtime UNKNOWN/TTL, reconcile recovery, vehicle command provider, site modules distributed B2, Step 3.5 architecture guards.

---

## 11. Performance (post deploy)

`scripts/performance-baseline.ps1` against prod (`192.168.50.54`):

| Route | 1 user p50 | 10 users p95 |
|-------|-----------|--------------|
| snapshot | ~99 ms | ~139 ms |
| dashboard | ~100 ms | ~841 ms |
| solar/forecast | ~151 ms | ~408 ms |

No unacceptable regression vs Step 3 module API Redis reads. Dashboard p95 under concurrent load remains within historical variance.

Results: `docs/performance/baseline-results-post-step3_5-deploy.json`

---

## 12. Production Acceptance

### Åkarp runtime

All divergent modules now **running** in API (matches Redis/collector).

### Denmark low-risk toggle (`feature.solar-forecast`)

```text
disabled → enable → running (after collector sync)
→ disable → stopped
→ restored to disabled
```

Transient `unknown` may appear immediately after enable before first Redis publish (~seconds).

---

## 13. Remaining Step 3 Debt (non-blocker)

| Item | Status |
|------|--------|
| `energy/builder.py` raw Heartbeat DTO parsing | MEDIUM — documented debt |
| `energy_balance/coordinator.py` sungrow_* field names | MEDIUM — normalized historical names |
| UI strings referencing Heartbeat in reasoning | Acceptable operator context |

---

## 14. Scripts

- `scripts/verify-prod-runtime-consistency.ps1` — API runtime consistency check
- `scripts/verify-prod-health.ps1` — unchanged health gate

---

## 15. Decision

All mandatory Step 3.5 fixes implemented, tested, and production-verified.

**READY FOR STEP 3 RE-VERIFICATION**
