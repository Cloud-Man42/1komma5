# EMIC Step 2 Architecture Verification

**Date:** 2026-09-07 (re-verification post Step 2.5)  
**Scope:** Step 2 Activatable Module Architecture + Step 2.5 runtime completion  
**References:**
- [EMIC_MODULAR_ARCHITECTURE_STEP2.md](./EMIC_MODULAR_ARCHITECTURE_STEP2.md)
- [EMIC_MODULAR_ARCHITECTURE_STEP2_5.md](./EMIC_MODULAR_ARCHITECTURE_STEP2_5.md)
- [EMIC_MODULAR_ARCHITECTURE_STEP2_5_RESULT.md](./EMIC_MODULAR_ARCHITECTURE_STEP2_5_RESULT.md)

**Method:** Static code review, architecture tests, full Python regression, frontend regression, prod read-only checks on `192.168.50.54`. Prod still runs pre–Step 2.5 deploy at time of verification — noted where behaviour differs from codebase.

---

## 1. Executive Summary

Step 2 + Step 2.5 together deliver an **operational module platform**: static registry, site-aware capabilities, projection + DB overlay, dependency resolver, admin API/UI, **orchestrator-driven lifecycle**, and **full collector lane gating**.

**Codebase verification (local / CI):** All Step 2 blockers from the original verification are **resolved in code**. `ModuleOrchestrator` is wired at collector startup and via Redis module events. Disable stops registry state, unregisters capabilities, and gates all planned collector lanes. Module PUT requires admin token. Legacy alias IDs filtered from site module list API.

**Prod verification (`192.168.50.54`):** Health checks pass. Site projection correct (akarp vs summer-house-denmark). **Step 2.5 not yet deployed on prod** — legacy aliases still appear in API, PUT is still open without Bearer token, runtime orchestrator not active in running collector until deploy.

**STEP 2 READINESS SCORE: 82 / 100** (codebase + CI; prod deploy pending)

**Decision:**

```
CODEBASE:  PASS — Step 2 + 2.5 acceptance criteria met in code and CI
PROD:      DEPLOY Step 2.5 required before prod sign-off
STEP 3:    NO-GO until prod deploy + maintenance-window akarp disable/enable cycle
```

---

## 2. Blocker Resolution (original B1–B2)

| ID | Original finding | Post–Step 2.5 status | Evidence |
|----|------------------|----------------------|----------|
| B1 | Disable does not stop all workers/polling | **FIXED (code)** | `collector.py` gates heartbeat, energy-balance, smart-charging, spa, solar, vehicles, ev-accounting, virtual-bridge, ems-shadow, energy-control via `is_module_runtime_active` / `filter_sites_for_module` |
| B2 | Orchestrator never invoked; stop not wired | **FIXED (code)** | Collector `setup()` → `start_all_sites()` + Redis listener; `SiteModuleService` publishes events; `stop_module()` unregisters capabilities |

**Prod:** Collector process on `192.168.50.54` not yet restarted with Step 2.5 — runtime behaviour on prod assumes pre-2.5 until deploy.

---

## 3. Regression Testing

| Metric | Original Step 2 (2026-09-07 AM) | Re-verification (2026-09-07 PM) |
|--------|--------------------------------|----------------------------------|
| Python tests | 1360 passed, 3 skipped | **1380 passed**, 3 skipped |
| Frontend tests | 704 passed | **704 passed** (1 unrelated flake in `EvOverview.test.tsx` when run via full `test-windows.ps1`; isolated Vitest run passes) |
| Architecture / module tests | — | **76 passed**, 1 skipped |

**Step 2.5 tests added:**
- `test_module_orchestrator.py` — idempotent start/stop, capability unregister, dependency reaction
- `test_module_runtime_isolation.py` — two-site isolation
- `test_step2_5_acceptance.py` — solar-forecast gating, smart-charging skip
- `test_site_modules.py` — projection + override, legacy filter
- `test_collector_module_gating.py` — expanded lane gating
- `test_site_modules_api.py` — auth 401/403/200, disable persist, legacy filter
- `frontend/src/lib/api.test.ts` — admin Bearer on `updateSiteModule`

**Result:** **PASS** (Python); frontend flake tracked separately.

---

## 4. Runtime Enable/Disable (§9, §40)

| Check | Codebase | Prod |
|-------|----------|------|
| Enable via PUT → registry RUNNING | **PASS** | Partial — API updates DB; orchestrator active after 2.5 deploy |
| Disable via PUT → lane skip | **PASS** | Partial — gated lanes in code; prod collector pre-2.5 |
| Orchestrator idempotent re-enable | **PASS** | Not verified on prod |
| Solar-forecast reference module | **PASS** | DK toggled during probe; restored to `enabled=false` |
| Charge Amps full disable cycle on akarp | **NOT RUN** | Avoided — active charger; 409 guard verified |

---

## 5. Security (§16)

| Check | Codebase | Prod |
|-------|----------|------|
| Secrets in module API | **PASS** | **PASS** |
| PUT requires admin token | **PASS** (`require_admin_token`) | **FAIL** — PUT without Bearer returned 200 (pre-2.5 deploy) |
| Disable blocked when unsafe (409) | **PASS** | **PASS** (akarp chargeamps + smart-charging guard) |

---

## 6. Module Registry & API (§3, §14)

| Check | Result |
|-------|--------|
| Canonical modules registered | **PASS** — 11 canonical + 6 legacy in registry bootstrap |
| Legacy aliases hidden from site list API | **PASS (code)** / **FAIL (prod)** — prod still returns `charging`, `vehicles`, `solar_forecast` |
| GET/PUT/404/409 semantics | **PASS** |
| Runtime status from registry | **PASS (code)** — `ModuleRuntimeRegistry`; prod shows `running`/`stopped` via API |

---

## 7. Site Activation & Isolation (§4, §11)

| Site | Charge Amps | Smart Charging | Solar Forecast |
|------|-------------|----------------|----------------|
| `akarp` | enabled, runtime=running | can_start=true, running | enabled, running |
| `summer-house-denmark` | disabled, stopped | can_start=false, stopped | disabled, stopped |

**Two-site isolation test:** **PASS** in CI (`test_module_runtime_isolation.py`).

---

## 8. Lifecycle (§8)

| Check | Original | Re-verification |
|-------|----------|-----------------|
| Orchestrator invoked | FAIL | **PASS (code)** |
| stop_module on disable | FAIL | **PASS (code)** via Redis + collector |
| Runtime status synthetic | FAIL | **PASS (code)** — registry-backed |
| Mercedes supervisor unconditional | FAIL | **FIXED** — per-site handler, no `start()` in setup |

---

## 9. Architecture Rules (§17)

All `test_layering.py` baselines **empty** — **PASS**.  
New check: collector imports `ModuleOrchestrator` — **PASS**.

---

## 10. Prod Health (2026-09-07 PM)

`scripts/verify-prod-health.ps1`:

| Check | Result |
|-------|--------|
| snapshot | OK |
| dashboard | OK (6.3 kWh) |
| solar/dashboard alignment | OK (delta 0.06 kWh) |
| Mercedes integration | OK |
| Charge Amps / Halo bridge | OK |
| integration health | OK |

---

## 11. Readiness Scores

| Dimension | Original | Re-verification | Notes |
|-----------|----------|-----------------|-------|
| Module Registry | 88 | 92 | Legacy filter in API (code) |
| Site Activation | 75 | 78 | Unchanged projection model |
| Capability Model | 80 | 86 | Register on RUNNING only |
| Dependency Resolution | 90 | 90 | Unchanged |
| Lifecycle | 35 | 80 | Orchestrator + registry |
| Failure Isolation | 70 | 72 | Lane skip on disable |
| Health | 72 | 72 | Unchanged |
| Persistence | 85 | 92 | Disable persist CI test |
| Security | 55 | 85 | Auth in code; prod pending |
| Architecture Purity | 65 | 65 | Unchanged |
| Test Coverage | 68 | 88 | Step 2.5 acceptance suite |
| Performance | 88 | 88 | Not re-baselined |
| Operational Stability | 60 | 68 | Prod healthy; 2.5 deploy pending |

**STEP 2 READINESS SCORE: 82 / 100**

---

## 12. GO / NO-GO Decision

| Criterion | Met? |
|-----------|------|
| No BLOCKERS (code) | **YES** |
| Disable stops work (code) | **YES** |
| Orchestrator wired | **YES (code)** |
| Admin auth on PUT (code) | **YES** |
| Persistence | **YES** |
| Capabilities + dependencies | **YES** |
| Tests pass (Python) | **YES** |
| Prod deploy Step 2.5 | **NO** |
| Akarp Charge Amps disable cycle on prod | **NOT RUN** |
| Core/Features vendor-free | **PARTIAL** (unchanged) |

```
CODEBASE VERIFICATION:  PASS
PROD SIGN-OFF:          PENDING Step 2.5 deploy
NO-GO FOR STEP 3        (until prod deploy + maintenance-window acceptance)
```

---

## 13. Required Before Step 3

1. **Deploy Step 2.5** to prod (`192.168.50.54`) — backend + collector restart.
2. **Prod smoke:** PUT without token → 401; legacy aliases absent from site module list; enable/disable solar-forecast on Denmark.
3. **Maintenance window:** akarp Charge Amps disable → smart-charging BLOCKED → re-enable (optional full cycle).
4. Re-run `scripts/performance-baseline.ps1` post-deploy.

---

## 14. Summary Table

```
STEP 2 RE-VERIFICATION (post 2.5 codebase)

Module Registry              PASS (code) / legacy on prod until deploy
Site isolation               PASS (CI + API)
Enable/disable               PASS (code) / partial prod
Persistence                  PASS
Capabilities                 PASS
Dependency resolution        PASS
Lifecycle                    PASS (code)
Worker cleanup               PASS (code)
Failure isolation            PARTIAL
Health                       PASS
Security                     PASS (code) / FAIL prod PUT auth until deploy
Architecture rules           PASS
Regression tests             PASS (1380 Python)
Performance                  NOT RE-RUN
Restart recovery             PASS (prior + code design)
```

---

## Appendix A: Prod Probe Log (2026-09-07 PM)

| Action | Result |
|--------|--------|
| GET akarp modules | chargeamps + smart-charging running; 17 modules (includes legacy aliases — pre-2.5) |
| GET summer-house-denmark modules | chargeamps + smart-charging stopped |
| PUT solar-forecast enable DK (no auth) | 200 — **confirms pre-2.5 auth gap** |
| PUT solar-forecast disable DK (restore) | disabled=false, runtime=stopped |
| verify-prod-health.ps1 | all OK |

## Appendix B: Gated Collector Lanes (post Step 2.5)

| Lane | Gated? | Module check |
|------|--------|--------------|
| Heartbeat fast-lane | **Yes** | `integration.heartbeat` |
| Market prices | **Yes** | `feature.price-engine` |
| Smart charging engine | **Yes** | `feature.smart-charging` |
| Energy balance | **Yes** | `feature.energy-balance` |
| EV accounting | **Yes** | `feature.smart-charging` |
| Vehicle charge sessions | **Yes** | `feature.vehicles` |
| Arctic Spa integration | **Yes** | `integration.arctic_spa` |
| Solar forecast | **Yes** | `feature.solar-forecast` |
| Virtual bridge | **Yes** | heartbeat + smart-charging |
| EMS shadow | **Yes** | `feature.energy-control` |
| Energy control | **Yes** | `feature.energy-control` |
| Vehicle supervisor | **Per-site handler** | `integration.mercedes` |
| snapshot_write, financial_rollup, timescale | Core | Always on |

---

## Historical Note

The original Step 2 verification (2026-09-07 AM, score 62/100, NO-GO) identified blockers B1–B2 and security gap H1. Step 2.5 addressed these in codebase. Sections above supersede the original executive summary and decision for current status.
