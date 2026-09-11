# Getting started

1. Create a Python package under `module/` with an entrypoint callable, e.g. `demo:build_module`.
2. Author `manifest.json` (see `module-manifest.schema.json`).
3. Build a ZIP `.emicpkg` with `manifest.json`, `module/`, optional `schemas/`, `migrations/`, `integrity/`.
4. Validate via `POST /api/modules/packages/validate` (admin).
5. Install via `POST /api/modules/packages/install` and restart backend/collector.

Reference module: `packages/energy-core/tests/fixtures/modules/integration.demo/`.
