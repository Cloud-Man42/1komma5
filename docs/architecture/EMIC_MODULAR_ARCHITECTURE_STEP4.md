# EMIC Step 4 – Module Manager, Device Onboarding & Operations UI

## Goal

Deliver a unified **Moduler & enheter** hub for per-site module lifecycle, device visibility, schema-driven configuration, read-only connection tests, and onboarding wizard entry points—without duplicating vendor logic in the frontend.

## Architecture

- **Backend source of truth:** `ModuleRegistry`, `SiteModuleResolver`, `DeviceRegistry`, onboarding handlers in `providers/module_onboarding.py`
- **Separate concerns:** Enabled / Runtime / Health (UNKNOWN runtime → “Runtime status unavailable” in UI)
- **Aggregated fetch:** `GET /api/sites/{slug}/operations` composes modules + devices + integration health
- **Secrets:** Config GET never returns secret values; PUT accepts empty secret fields as “keep existing”

## New / extended API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/system/onboarding-catalog` | Categories → onboardable modules + schemas |
| `GET /api/system/modules` | Extended with `configuration_schema`, onboarding metadata |
| `GET/PUT /api/sites/{slug}/modules/{id}/config` | Admin; validated config persistence |
| `POST /api/sites/{slug}/modules/{id}/test-connection` | Read-only connection test (rate-limited) |
| `POST /api/sites/{slug}/modules/{id}/discover` | Device discovery where supported |
| `GET /api/sites/{slug}/operations` | Hub aggregate |

## Frontend

- Nav: **Moduler & enheter** → `/config/modules-devices`
- Sub-routes: modules list/detail, devices list/detail, add-device wizard
- Shared components under `frontend/src/components/modules-devices/`
- Link from legacy `/config/system` panel

## Live integrations (MVP wizard paths)

| Module | Category | Handler |
|--------|----------|---------|
| `integration.chargeamps` | EV charger | `chargeamps` |
| `integration.mercedes` | Vehicle | `mercedes` (real REST test) |
| `integration.heartbeat` | Energy provider | `heartbeat` |
| `integration.arctic_spa` | Spa | `arctic_spa` |

## Out of scope (Step 5)

- Module Store / marketplace / dynamic plugins
- Physical device control from Module Manager

## Verification

See `EMIC_MODULAR_ARCHITECTURE_STEP4_RESULT.md` for acceptance table and prod checklist.
