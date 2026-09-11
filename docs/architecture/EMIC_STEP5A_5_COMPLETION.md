# EMIC Step 5A.5 — Security, Runtime & Production Completion

Step 5A.5 closes the verified Step 5A gaps (blockers B1–B2, highs H1–H5, mediums M1–M6) without building Step 5B marketplace/store UI.

## Baseline (pre-change)

| Suite | Collected | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Python | 1450 | 1444 | 0 | 6 |
| Frontend | 714 | 714 | 0 | 0 |
| Step 5A package tests | 19 | 19 | 0 | 0 |

## Final regression

| Suite | Collected | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Python | 1457 | 1457 | 0 | 6 |
| Frontend | 714 | 714 | 0 | 0 |
| Package tests | 22 | 22 | 0 | 0 |

## Delivered

### Cryptographic trust (B2)
- Ed25519 sign/verify via `cryptography` (`signing.py`, `integrity.py`)
- Canonical manifest + content digest model (`canonical.py`)
- Publisher trust store DB table + memory/config loader (`trust_store.py`, migration `064_module_publisher_keys`)
- Separate validation semantics: `valid`, `signed`, `signature_valid`, `publisher_trusted`, `install_allowed`

### Integrity & quarantine (H2, M4)
- Startup revalidation in `load_installed_module_packages()`
- QUARANTINED state persisted with reason/timestamp/metadata
- ZIP bomb guards, path traversal rejection, entry limits

### Runtime (H1)
- Generic package capability registration from `ModuleDescriptor.provided_capabilities` in `site_modules.py`
- Package runtime E2E test (`test_package_runtime.py`)

### Lifecycle policy (H3, H5)
- Default downgrade block with `VERSION_DOWNGRADE_NOT_ALLOWED`; explicit `allow_downgrade` on update API
- Config migration runner for major bumps
- Pre-promote health gate; rollback only after successful promotion
- Capability removal impact analysis

### Permissions (H4)
- Allowlist + capability/permission coupling (`permissions.py`)
- Docs updated to state install-time validation, not sandbox enforcement

### Guards (M1–M3, M5)
- Impact endpoint admin auth
- `platform.*` protected namespace
- Device remove guard (`MODULE_HAS_DEVICES`)
- Per-module mutation lock

### Production (B1)
- Deployed to `192.168.50.54` via `scripts/deploy.local.ps1`
- `GET /api/modules/packages` → 200
- Post-deploy health + runtime consistency PASS

### Tests & docs (M6)
- Expanded package test matrix (security, runtime, rollback, remove, dependencies)
- `docs/module-sdk/security.md`

## Not in scope (Step 5B)
Module Store UI, remote catalog, publisher portal, marketplace, remote download, ratings/reviews.

## Re-verification
Run independent **EMIC STEP 5A VERIFICATION** before any Step 5B work.
