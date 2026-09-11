# EMIC Step 2 Result Report

**Date:** 2026-09-07  
**Scope:** Activatable Module Architecture

## Summary

Step 2 delivers an operational module platform: registry, capabilities, site activation (projection + DB overlay), dependency resolver, collector/charging gating, API, and minimal admin UI.

## Files Changed (key)

### Platform core
- `platform/capabilities/types.py`, `registry.py` — Capability model + site-aware registry
- `platform/modules/registry.py` — extended `ModuleDescriptor`
- `platform/modules/bootstrap.py` — integration + feature modules + legacy aliases
- `platform/modules/resolver.py` — `ModuleDependencyResolver`
- `platform/modules/site_modules.py` — `SiteModuleResolver` (projection-first)
- `platform/modules/runtime.py`, `orchestrator.py`, `gating.py`, `aliases.py`, `types.py`
- `db/models/modules.py`, `db/site_module_repo.py`
- `alembic/versions/062_site_module_configurations.py`

### Runtime wiring
- `charging/engine.py` — module gating before charger cycle
- `collector/app/collector.py` — spa/solar lane gating
- `config.py` — `EMIC_MODULE_GATE_ENABLED`

### API / UI
- `backend/app/api/site_modules.py`
- `backend/app/api/system.py` — extended module list
- `frontend/src/components/config/SiteModulesPanel.tsx`
- `frontend/src/app/config/system/page.tsx`
- `frontend/src/lib/api.ts` — `fetchSiteModules`, `updateSiteModule`

## Database Migrations

- `062_site_module_configurations` — optional per-site enable override

## Modules Registered

**Integrations:** `integration.heartbeat`, `integration.chargeamps`, `integration.mercedes`, `integration.arctic_spa`  
**Features:** `feature.smart-charging`, `feature.vehicles`, `feature.spa-energy`, `feature.energy-balance`, `feature.solar-forecast`, `feature.price-engine`, `feature.energy-control`  
**Legacy aliases:** `charging`, `vehicles`, `spa_energy`, etc.

## Capabilities Registered (per site at resolve time)

Charge Amps → EV charger control; Mercedes → vehicle telematics; Heartbeat → grid/solar/battery/price; Spa → temperature/power; Solar → forecast.

## Site-Specific Activation

Implemented via projection + `site_module_configurations.enabled_override`.

## Dependency Resolver

`CanStart`, `CanDisable`, topological startup order, cycle detection — tested.

## Lifecycle

`ModuleOrchestrator` scaffold; collector uses gating (`EMIC_MODULE_GATE_ENABLED`).

## Health

Module health derived from `integration_health` provider mapping.

## API Changes

New site module endpoints; extended `/api/system/modules`.

## Tests Added

- `test_capability_registry.py`, `test_module_resolver.py`, `test_step2_acceptance.py`
- `test_module_characterization.py`, `test_collector_module_gating.py`
- `backend/tests/test_site_modules_api.py`
- `frontend/.../SiteModulesPanel.test.tsx`

## Tests Passed

Full suite via `.\test-windows.ps1` — **1360+ Python**, **704 frontend** (after Step 2 completion).

## Performance

Module resolution cached per site (30s TTL). No per-datapoint resolver calls in dashboard.

## Remaining Direct Couplings

- Collector still constructs coordinators directly (gated, not registry-driven lifecycle)
- Legacy parallel trees (`heartbeat/`, `sungrow/`, `vehicles/mercedes/`) unchanged
- `DeviceCapability` enum retained for charger framework; `Capability` enum for module platform

## Known Technical Debt

- Full `ModuleOrchestrator` wiring for all collector lanes
- Provider primary/fallback selection policy
- Module config JSON validation per `configuration_schema`

## Breaking Changes

None for existing sites — projection preserves current enable state.

## Rollback Procedure

1. Set `EMIC_MODULE_GATE_ENABLED=false`
2. `alembic downgrade 061` to drop overlay table
3. Redeploy previous image if needed
