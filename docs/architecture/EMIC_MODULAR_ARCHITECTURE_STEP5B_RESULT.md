# EMIC Step 5B – Internal Module Store Result

**Date:** 2026-09-07  
**Scope:** Internal / trusted packages only — **not** public marketplace

## Summary

Step 5B adds admin UI and backend read models for an **Internal Module Store** on top of Step 5A package foundation. Administrators can upload, validate, review trust/impact, install, restart, enable per site, update, rollback, and remove trusted `.emicpkg` modules without SSH or manual file copy.

Backend remains source of truth for all trust, signature, dependency, and install eligibility decisions.

## STEP 5B ACCEPTANCE

| Item | Status |
|------|--------|
| Store overview | PASS |
| Installed packages | PASS |
| Available trusted packages | PASS |
| Needs-attention view | PASS |
| Package upload | PASS |
| Validation preview | PASS |
| Signature status | PASS |
| Publisher trust display | PASS |
| Permissions review | PASS |
| Capabilities review | PASS |
| Dependencies review | PASS |
| Impact analysis | PASS |
| Install | PASS |
| Install error handling | PASS |
| Restart-required UX | PASS |
| Site activation handoff | PASS |
| Update | PASS |
| Downgrade protection | PASS |
| Config migration UX | PASS (backend-owned; UI shows message when returned) |
| Health rollback UX | PASS (backend health gate; UI shows API message) |
| Manual rollback | PASS |
| Remove | PASS |
| Dependency remove guard | PASS |
| Device remove guard | PASS |
| Historical data policy | PASS (UI note) |
| Quarantine display | PASS |
| Quarantined enable blocked | PASS |
| Publisher list | PASS |
| Publisher add | PASS |
| Publisher revoke | PASS |
| Private-key exclusion | PASS |
| Unsigned prod policy | PASS |
| Loader startup trust policy | PASS |
| Tamper startup test | PASS |
| Revoked-key test | PASS |
| Runtime version truth | PARTIAL (heartbeat fields added; full prod consistency deferred) |
| Multi-site package isolation | PASS (existing site module gating + store site view) |
| Signed demo prod lifecycle | SAFELY DEFERRED |
| Security | PASS |
| Audit | PASS (existing admin audit on mutations) |
| Architecture tests | PASS |
| Frontend tests | PASS |
| Backend tests | PASS |
| Regression | PASS (after loader settings fix) |
| Performance | PASS (metadata list; no disk scan per card) |
| Production health | DEFERRED (deploy pending operator run) |

## Key deliverables

### Backend
- `PackageStoreService.build_overview()` — installed / catalog / needs_attention
- Store + sites endpoints on `module_packages.py`
- `module_publishers.py` — list/add/revoke trusted public keys
- Loader accepts app `Settings` for unsigned startup policy parity
- Quarantine blocks site enable (`PACKAGE_QUARANTINED`)

### Frontend
- Routes: `/config/modules-devices/store`, `.../upload`, `.../store/[moduleId]`, `.../publishers`
- Components: `ModuleStoreOverview`, `PackageUploadWizard`, `PackageStoreDetailPanel`, `PublishersPanel`, `ModulesDevicesNav`
- Module Manager link: "Visa paketdetaljer" for installed packages
- Human error mapping in `packageErrorLabels.ts`

### Tests added
- `test_package_loader_startup.py` — unsigned prod policy, tamper, revoked key
- `test_module_store_api.py` — overview, prod validate block, publishers
- Frontend: store list, upload validation/install, error labels

## Known deferrals

1. **Signed demo prod E2E** — not run live; safe to execute on staging with trusted keys
2. **Runtime version consistency prod verify** — `verify-prod-runtime-consistency.ps1 -Strict` after deploy
3. **Public marketplace** — explicitly NO-GO per Step 5A verification

## Blockers checked

| Blocker | Status |
|---------|--------|
| UI allows untrusted install override | No |
| Trust decision in frontend | No |
| Unsigned prod load after policy change | Blocked at loader |
| Revoked package loads after restart | Quarantined |
| Quarantined enable | Blocked |
| Install bypass package services | No |
| Arbitrary URL fetch | No |
| Private keys in runtime | No |
| Unauthenticated mutations | No |
| Step 4 regression | Tests pass |

## Decision

**READY FOR STEP 5B VERIFICATION**

(Public marketplace remains **not ready** and out of scope.)
