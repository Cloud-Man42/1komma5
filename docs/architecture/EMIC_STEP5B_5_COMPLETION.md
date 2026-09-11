# EMIC Step 5B.5 — Production Deployment, Auth & Store Completion

Date: 2026-09-07

## Scope

Step 5B.5 closes verified Internal / Trusted Module Store gaps from `EMIC_STEP5B_VERIFICATION.md` (score 62/100, NO-GO for Step 5C). This is **not** Step 5C — no public marketplace, remote catalog, or third-party install.

## Baseline (pre-change)

| Suite | Result |
| --- | --- |
| Python | 1464 passed, 6 skipped |
| Frontend | 720 passed |
| Architecture / package / store / security | PASS |

## Changes delivered

### B1 — Production deployment

- Deployed Step 5B.5 to `192.168.50.54` via `scripts/deploy.local.ps1`.
- Verified Store UI routes return 200: `/config/modules-devices/store`, `/upload`, `/publishers`, package detail.
- Post-deploy health and runtime consistency scripts PASS.

### H1 — Package read auth

- `GET /api/modules/packages` and `GET /api/modules/packages/{module_id}` require `require_admin_token`.
- Replaced filesystem `package_path` exposure with `logical_package_id`.
- Added API tests: anonymous → 401, admin → 200.

### H2 — Signed demo production lifecycle

- Added `scripts/sign_demo_packages.py` (private key in temp dir only, never repo/container/DB).
- Added `scripts/step5b5-prod-acceptance.ps1` for full prod lifecycle.
- Executed on prod: validate → impact → install → restart → enable (akarp) → version truth → update 1.1 → downgrade block → rollback → disable → remove → revoke publisher.
- Fixed validate endpoint to pass `PublisherTrustStore` (signed packages were rejected before fix).
- Fixed loader startup checksum to ignore `__pycache__`/`.pyc` so restart no longer quarantines loaded packages.

### M1 — Catalog validate/impact preview

- Backend: `POST /api/modules/packages/catalog/{entry_id}/validate` and `/impact`.
- Frontend catalog cards use shared `PackageReviewPanel` (validate → trust → impact → confirm → install).

### M2 — Trust read model

- `trust_read_model.py` persists and reads `signed`, `signature_valid`, `publisher_trusted`, `publisher_status`, `install_allowed`.
- Store overview/detail use persisted metadata — no per-render crypto revalidation.

### M3 — Package detail / update UX

- Dedicated `GET /api/modules/packages/store/packages/{module_id}` detail endpoint.
- Expanded `PackageStoreDetailPanel`: trust, permissions, capabilities, dependencies, runtime/checksum, quarantine diagnostics, rollback impact.
- `PackageUploadWizard` honors `?update=` for update mode via `updateModulePackage`.

### M4 — Quarantined enable test

- `test_quarantined_package_enable_blocked` → 409 `PACKAGE_QUARANTINED` through site module API path.

### M5 — Runtime version/checksum truth

- Store service compares installed vs runtime version/checksum from Redis heartbeat.
- Exposes `version_match`, `checksum_match`, `needs_attention` on mismatch (package-managed modules only).

### M6 — Test expansion

- Frontend: catalog review flow, upload wizard update param, store overview tests.
- Backend: package read auth, signed validate trust store, quarantine enable, publisher re-trust.
- Package loader: second-startup survival after import (`__pycache__` fix).

### Publisher admin

- Re-trust revoked publisher keys via `POST /api/modules/publishers` (same publisher_id/key_id).

## Post-change regression

| Suite | Result |
| --- | --- |
| Python | 1473 passed, 6 skipped |
| Frontend | 721 passed (152 files) |
| Prod acceptance script | PASS |
| Prod health | PASS |
| Prod runtime consistency (-Strict) | PASS |

## Production acceptance evidence

- Anonymous package list/detail → 401.
- Admin store overview → 200.
- Signed `integration.demo` validate/install/update/rollback/remove on prod.
- Multi-site isolation: enabled on `akarp`, disabled on `summer-house-denmark`.
- `installed_version=1.0.0`, `runtime_version=1.0.0`, `version_match=true` after load.
- Downgrade 1.1 → 1.0 blocked with `VERSION_DOWNGRADE_NOT_ALLOWED`.
- Test publisher revoked after demo; prod health unchanged.

## Intentionally not in scope

- Public marketplace / remote package download
- Public publisher signup
- Step 5C features

## Next step

Re-run **EMIC STEP 5B — INDEPENDENT VERIFICATION** before any Step 5C design work.
