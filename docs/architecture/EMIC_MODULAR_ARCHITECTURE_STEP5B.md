# EMIC Step 5B – Internal / Trusted Module Store

## Scope

Step 5B delivers an **admin-only Internal Module Store** for trusted EMIC packages. It is **not** a public marketplace.

### In scope

- Installed package overview, needs-attention view, internal trusted catalog
- Upload `.emicpkg` → validate → impact → install (backend is source of truth)
- Trust display (signed, signature valid, publisher trusted, install allowed)
- Permissions / capabilities / dependencies review (presentation only)
- Update, rollback, remove via existing package APIs
- Restart-required UX (reuse Step 4 operations pattern)
- Site activation handoff to Module Manager (install ≠ enable)
- Publisher trust list / add public key / revoke key
- Quarantine UX and enable blocking
- Loader startup trust policy aligned with install policy

### Explicitly out of scope

- Remote URL install, public publisher onboarding, marketplace discovery
- Ratings, licensing, community packages, unsigned prod override UI
- Frontend signature validation, SemVer comparison, dependency resolution
- Private signing keys in EMIC runtime

## Information architecture

```
Settings → Moduler & enheter
├── Översikt
├── Moduler          (Module Manager — per-site enable/config)
├── Module Store     (/config/modules-devices/store)
├── Publishers       (/config/modules-devices/publishers)
└── Enheter
```

Package detail: `/config/modules-devices/store/{moduleId}`  
Upload: `/config/modules-devices/store/upload`

## Backend

| Component | Location |
|-----------|----------|
| Store read model | `packages/energy-core/.../packages/store_service.py` |
| Internal catalog | `packages/energy-core/.../packages/catalog.py` |
| Package API extensions | `backend/app/api/module_packages.py` |
| Publisher trust API | `backend/app/api/module_publishers.py` |
| Startup revalidation | `packages/energy-core/.../packages/loader.py` |

### Store API

- `GET /api/modules/packages/store/overview` — installed, catalog, needs_attention
- `GET /api/modules/packages/{module_id}/sites` — per-site enablement
- `POST /api/modules/packages/catalog/{entry_id}/install` — catalog install (same validation path)
- Existing validate/install/update/rollback/remove/impact endpoints unchanged

### Publisher API (admin)

- `GET /api/modules/publishers`
- `POST /api/modules/publishers` — Ed25519 public key hex only
- `POST /api/modules/publishers/{publisher_id}/{key_id}/revoke`

### Settings

- `EMIC_MODULE_CATALOG_PATH` — JSON catalog pointing to controlled local `.emicpkg` files
- `EMIC_ALLOW_UNSIGNED_MODULES` — dev only; prod blocks unsigned at validate, install, and loader startup

## Frontend

| Component | Location |
|-----------|----------|
| Subnav | `ModulesDevicesNav.tsx` |
| Store overview | `ModuleStoreOverview.tsx` |
| Upload wizard | `PackageUploadWizard.tsx` |
| Package detail | `PackageStoreDetailPanel.tsx` |
| Publishers | `PublishersPanel.tsx` |
| Error labels | `packageErrorLabels.ts` |
| API client | `frontend/src/lib/api.ts` |

Frontend never decides trust or install eligibility — it renders backend fields and disables actions when `install_allowed=false`.

## Security boundaries

1. All package mutations require admin token
2. Trust/signing/dependency decisions remain in `PackageValidator` + `PublisherTrustStore`
3. Quarantined packages cannot be enabled (`PACKAGE_QUARANTINED`)
4. Loader revalidates checksum + signature (+ unsigned policy) on startup; failures → `QUARANTINED`
5. Revoked publisher keys cause startup rejection / quarantine on revalidation

## Runtime version truth

Collector orchestrator publishes `module_version` and `package_checksum` in runtime heartbeat when available. Store UI shows `installed_version` separately from `runtime_version` and flags mismatch.

## Tests

- Backend: `backend/tests/test_module_store_api.py`, package loader startup tests
- Frontend: `ModuleStoreOverview.test.tsx`, `PackageUploadWizard.test.tsx`, `packageErrorLabels.test.ts`
- Architecture: Step 5A guards remain; Store UI has no signature logic

## Production model

Deploy Step 5B UI + APIs. Internal catalog optional. Signed packages require trusted publisher keys in DB. Unsigned packages blocked when `EMIC_ALLOW_UNSIGNED_MODULES=false`.

Signed demo prod lifecycle (`integration.demo`) may be run when internal keys and staging policy allow — not required for public marketplace readiness.

## Future: Step 5C

Public marketplace would require separate verification (remote distribution, publisher governance, supply-chain monitoring). **Not built in Step 5B.**
