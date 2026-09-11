# EMIC Step 4.5 – Completion & Production Hardening

## Scope

Step 4.5 completes Module Manager / Device Manager so configuration, credentials, onboarding, runtime, and health are truthful end-to-end. This phase does **not** include Step 5 (Module SDK, store, dynamic loading).

## Baseline (pre-change)

| Suite | Count |
|-------|-------|
| Python collected | 1426 → 1435 |
| Frontend Vitest | 708 → 713 |
| Architecture guards | PASS |
| Step 4 backend | 19 passed, 1 skipped |

## Post-change regression

| Suite | Result |
|-------|--------|
| Python | 1428 passed, 6 skipped (1435 collected) |
| Frontend | 713 passed |
| Architecture guards | PASS |
| Step 4.5 API tests | 6 passed |

## Credential / config ownership

| Integration | Credentials | Device | Runtime |
|-------------|-------------|--------|---------|
| Heartbeat | `HeartbeatSettingsRepository` (global) + site `external_system_id` | Solar arrays via Heartbeat projection | Collector via `integration.heartbeat` module |
| Charge Amps | `EvChargerRepository.chargeamps_api_key` per charger; pending keys in `SiteModuleRepository._secure` | `EvChargerRepository` | Collector via `integration.chargeamps` |
| Mercedes | `VehicleProviderRepository` | `VehicleModel` | Collector via `integration.mercedes` |
| Arctic Spa | `ConsumerRepository` spa config | `EnergyConsumerModel` | Collector via `integration.arctic_spa` |

Generic `ModuleConfigService` delegates to `providers/module_config_handlers.py` (`MercedesConfigHandler`, `ChargeAmpsConfigHandler`, `HeartbeatConfigHandler`, `ArcticSpaConfigHandler`).

## Restart / apply semantics

1. `PUT .../config` persists and returns `restart_required`, `configuration_active`, `configuration_status`.
2. UI shows **ConfigurationStatusBanner** with explicit states and **Tillämpa ändringar** when restart is required.
3. `POST .../modules/{id}/apply` publishes `{ action: "restart" }` via Redis; collector stops/starts module.
4. Apply failures surface in UI; no false "Configuration active".

Runtime enable/disable remains collector-owned: API uses `apply_runtime=False` and publishes state via `publish_module_state_change`.

## Onboarding transaction policy (Charge Amps)

```
validate external_device_id
→ duplicate check (409 DEVICE_ALREADY_EXISTS)
→ create EvCharger
→ test connection
→ on failure: delete charger (rollback)
→ enable integration.chargeamps
→ publish runtime event
```

Resumable failures return structured errors; no ghost Healthy state.

## Key changes

### Backend
- `POST /api/sites/{slug}/modules/{module_id}/apply`
- `POST /api/sites/{slug}/modules/{module_id}/onboard`
- `GET /api/sites/{slug}/devices/{device_type}/{device_id}`
- Config response: `configuration_active`, `effectively_configured`, `configuration_status`
- Audit: `module.enabled`, `module.disabled`, `module.config.apply`, `device.onboarded`
- `integration.heartbeat` `can_disable=false`
- Connection test rate limit test (M5)

### Frontend
- Full Add Device wizard (10 steps): category → provider → site → config → test → discovery → selection → capabilities → activate → result
- Dynamic sites from `/api/sites`
- Structured 409 parsing (`lib/apiError.ts`)
- Module detail: capabilities tab, config status, apply/restart
- Device detail: single-device API (no `/operations` refetch)
- Runtime polling hook during transitions

## Production deployment

Deployed to `192.168.50.54` via `scripts/deploy-linux.ps1`.

Verified:
- `GET /api/sites/akarp/operations` → 200
- `GET /api/system/onboarding-catalog` → 200
- `/config/modules-devices` → 200
- `verify-prod-health.ps1` → PASS
- `verify-prod-runtime-consistency.ps1 -Strict` → PASS

## Security

- Admin token required for config PUT, apply, onboard, discover, test-connection, enable/disable
- Secrets masked in GET; not in audit payloads
- Mercedes credentials delegated to authoritative repository (tested)
