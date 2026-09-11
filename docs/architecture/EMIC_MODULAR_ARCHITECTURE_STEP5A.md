# EMIC Step 5A – Module SDK & Package Foundation

## Goal

Introduce a package layer above the existing module runtime without replacing `ModuleRegistry`, `ModuleOrchestrator`, or site activation.

## Package format

- **`.emicpkg`** — ZIP archive with `manifest.json`, `module/`, optional `schemas/`, `migrations/`, `integrity/`
- **Activation:** restart-based (`restart_required=true` after install/update/rollback/remove)
- **Install ≠ enable** — site enable remains in `site_module_configurations`

## New components

| Area | Location |
|------|----------|
| SDK contracts | `packages/energy-core/src/energy_core/platform/modules/sdk/` |
| Package services | `packages/energy-core/src/energy_core/platform/modules/packages/` |
| DB registry | `installed_module_packages` (migration 063) |
| Admin API | `backend/app/api/module_packages.py` |
| Reference module | `packages/energy-core/tests/fixtures/modules/integration.demo/` |
| Docs | `docs/module-sdk/` |

## Settings

- `EMIC_MODULES_PATH` — installed package root
- `EMIC_ALLOW_UNSIGNED_MODULES` — default `false` (dev/test only)
- `EMIC_VERSION` / `EMIC_MODULE_API_VERSION` — compatibility gates
- `EMIC_MODULE_PACKAGE_MAX_BYTES` — default 50MB

## API routes (admin)

- `POST /api/modules/packages/validate`
- `POST /api/modules/packages/install`
- `POST /api/modules/packages/{module_id}/update`
- `POST /api/modules/packages/{module_id}/rollback`
- `DELETE /api/modules/packages/{module_id}`
- `GET /api/modules/packages`, `GET .../{module_id}`, `POST .../impact`

## Startup sequence

```
register_default_modules()
BuiltInModuleAdapter.enrich_registry()
load_installed_module_packages()   # backend lifespan + collector setup
register_default_module_handlers()
```

## Out of scope (Step 5B)

Module Store UI, remote catalog, marketplace, hot-load.

## Production strategy

Deploy without installing third-party packages. Optional `integration.demo` only when `EMIC_ALLOW_UNSIGNED_MODULES=true` on staging.
