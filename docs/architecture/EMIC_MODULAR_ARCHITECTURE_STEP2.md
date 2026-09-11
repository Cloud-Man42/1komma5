# EMIC Modular Architecture — Step 2

Step 2 makes the modular monolith **operational**: modules can be registered, activated per site, resolved against capabilities, and observed via API/UI.

## 1. Module Model

`ModuleDescriptor` ([`registry.py`](../../packages/energy-core/src/energy_core/platform/modules/registry.py)):

- `module_id` — stable ID (`integration.chargeamps`, `feature.smart-charging`)
- `module_type` — `core | feature | integration | provider`
- `capabilities_provided`, `capabilities_required`, `optional_capabilities`
- `dependencies` — other EMIC modules (not vendors)
- Legacy aliases (`charging` → `feature.smart-charging`) for backward compatibility

## 2. Module Registry

Static in-process registry populated at startup via [`bootstrap.py`](../../packages/energy-core/src/energy_core/platform/modules/bootstrap.py) from backend and collector.

## 3. Capability Registry

[`Capability`](../../packages/energy-core/src/energy_core/platform/capabilities/types.py) enum + [`CapabilityRegistry`](../../packages/energy-core/src/energy_core/platform/capabilities/registry.py).

Providers register per `(site_id, capability, module_id, device_id?)`. Multiple providers per capability are supported.

## 4. Site Activation

[`SiteModuleResolver`](../../packages/energy-core/src/energy_core/platform/modules/site_modules.py) derives enabled state from existing tables (projection-first):

| module_id | Projection |
|-----------|------------|
| `integration.heartbeat` | `site.external_system_id` + global client |
| `integration.chargeamps` | any `ev_chargers.bridge_enabled` |
| `integration.mercedes` | `vehicle_provider_connections.enabled` |
| `integration.arctic_spa` | spa consumer + config + `ARCTIC_SPA_ENABLED` |
| `feature.solar-forecast` | `solar_site_configurations.enabled` |
| `feature.smart-charging` | any bridge-enabled charger |

Optional DB overlay: `site_module_configurations` (`enabled_override`) via migration `062`.

## 5. Dependency Resolution

[`ModuleDependencyResolver`](../../packages/energy-core/src/energy_core/platform/modules/resolver.py):

- `can_start(module, site)` — required capabilities + module deps
- `can_disable(module, site)` — blocks if dependents lose capabilities
- `startup_order()` — topological sort with cycle detection

## 6. Module Lifecycle

[`ModuleLifecycle`](../../packages/energy-core/src/energy_core/platform/lifecycle.py) + [`ModuleOrchestrator`](../../packages/energy-core/src/energy_core/platform/modules/orchestrator.py).

Collector uses **gating** ([`gating.py`](../../packages/energy-core/src/energy_core/platform/modules/gating.py)) rather than full orchestrator replacement.

## 7. Health Model

- **Activation:** `enabled | disabled`
- **Runtime:** `stopped | starting | running | blocked | failed`
- **Health:** `healthy | degraded | unavailable | unknown`

Integration health providers map to module IDs via `INTEGRATION_PROVIDER_MODULE_MAP`.

## 8. Configuration Model

Integration config remains in existing tables (encrypted credentials). `site_module_configurations.config_json` is reserved for non-secret overlays only.

## 9. Persistence

- Source of truth: existing integration tables
- Overlay: `site_module_configurations` (dual-read)
- Safe default: projection enables everything currently active; no auto-disable on deploy

## 10. Provider Resolution

`CapabilityRegistry.providers_for(site, capability)` returns all providers. No primary/fallback policy engine in Step 2.

## 11. Failure Isolation

Module startup failures set `runtime_status=failed` without stopping other modules. Smart charging degrades when Heartbeat unavailable (existing `_degraded_energy_state`).

## 12. API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/system/modules` | Global module catalog |
| `GET /api/sites/{slug}/modules` | Per-site status |
| `GET /api/sites/{slug}/modules/{module_id}` | Detail |
| `PUT /api/sites/{slug}/modules/{module_id}` | Enable/disable with dependency check |

## 13. Security

No secrets in module API responses. Disable blocked when dependents would lose required capabilities.

## 14. Testing

Platform tests: registry, capabilities, resolver, acceptance scenario §46, site API, collector gating, charging gating.

## 15. Migration

1. Deploy code with projection-only reads
2. Run Alembic `062_site_module_configurations`
3. Enable/disable via API writes overlay rows only

## 16. Rollback

- `alembic downgrade -1` — drop overlay table; projection continues
- `EMIC_MODULE_GATE_ENABLED=false` — skip collector/engine gating checks
