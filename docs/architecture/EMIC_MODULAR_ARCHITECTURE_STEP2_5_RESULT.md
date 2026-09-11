# EMIC Step 2.5 – Runtime Completion Result

**Date:** 2026-09-07  
**Decision:** READY FOR STEP 2 RE-VERIFICATION (not GO FOR STEP 3)

## Summary

Step 2.5 wires the module platform into collector runtime:

- `ModuleOrchestrator` used at collector startup and on Redis module events
- Lane gating via `is_module_runtime_active` (DB enabled + registry `RUNNING`)
- `SiteModuleService` + Redis pub/sub for cross-process enable/disable
- Module PUT protected with `require_admin_token`
- Legacy alias IDs filtered from API list responses
- Mercedes supervisor started per-site via handler (not unconditional global start)

## Acceptance table (§56)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Disable stops lane work | PASS | Collector gates all planned lanes; tests in `test_collector_module_gating.py`, `test_step2_5_acceptance.py` |
| Orchestrator wired in production path | PASS | `collector.py` startup + Redis listener; `test_layering.py` |
| Real runtime status (not synthetic) | PASS | `SiteModuleResolver.list_modules` reads `ModuleRuntimeRegistry` |
| Module PUT admin auth | PASS | `test_site_modules_api.py` 401/403/200 |
| Disable persists after reload | PASS | `test_disable_module_persists_override` |
| Legacy alias filter | PASS | `test_list_modules_excludes_legacy_alias_ids` |
| Two-site isolation | PASS | `test_module_runtime_isolation.py` |
| Orchestrator idempotent start/stop | PASS | `test_module_orchestrator.py` |
| Solar-forecast reference module E2E | PASS | `test_step2_5_acceptance.py` |
| Dependency reaction | PASS | `test_dependency_reaction_blocks_smart_charging_when_chargeamps_stopped` |
| Frontend admin headers on PUT | PASS | `api.test.ts` updateSiteModule |

## Blockers fixed from Step 2 verification

1. Disable did not stop polling → lane gating + orchestrator stop
2. Orchestrator never called → collector startup + Redis subscriber
3. Synthetic RUNNING status → registry-backed status
4. Module PUT unauthenticated → `require_admin_token`
5. Missing acceptance tests → new platform/collector/backend/frontend tests

## Remaining debt

- Prod read-only verification on `summer-house-denmark` solar-forecast toggle (manual)
- Performance baseline comparison (optional; script exists)
- Backend process does not run orchestrator locally (by design; collector owns runtime)

## Rollback

Set `EMIC_MODULE_GATE_ENABLED=false` to bypass gates. Redis failure degrades to periodic dirty-site sync.
