# EMIC Sprint D.5 — Production Deployment & Store Acceptance Closure

**Date:** 2026-09-08  
**Target:** `192.168.50.54`  
**Verdict:** **READY FOR SPRINT D VERIFICATION**

---

## Summary

Sprint D.5 closed the production deployment blocker. Sprint D Module Store code is deployed, reachable at `/config/modules-devices/store`, and passes production acceptance smoke tests. Safety boundaries remain intact: `THIRD_PARTY_RUNTIME_ENABLED=false`, `CONTROL_ISOLATION_GATE_OPEN=false`, no third-party runtime processes started.

---

## Root cause — remote extract failure

### What failed

Initial `scripts/deploy-linux.ps1` runs failed during remote archive extraction on `192.168.50.54`:

```text
tar: packages/energy-core/tests/fixtures/modules/integration.sandbox-demo/.build: Cannot utime: Operation not permitted
```

Subsequent attempts also failed when replacing the live `packages/` tree:

```text
rm: cannot remove 'packages/energy-core/.../__pycache__': Permission denied
```

### Cause

1. **Archive contained test fixture `.build` directories** created by prior Docker test runs on the production host with root ownership.
2. **In-place extraction** (`tar -xzf … -C ~/energy-monitoring`) attempted to overwrite root-owned files; `tar` failed on `utime` and permission conflicts.
3. **Partial prior deploy state** left root-owned `__pycache__` under the live tree, blocking `rm -rf packages`.

Contributing factors: archive corruption/truncation, missing tools, disk space, CRLF, and SSH truncation were **ruled out** — local and remote SHA-256 matched; `tar`/`gzip` present; disk space sufficient.

### Fix

| Change | Purpose |
|--------|---------|
| `scripts/deploy-linux-extract.sh` (new) | Staging extract → SHA-256 verify → disk check → validate content → atomic swap into live tree |
| Archive excludes in `deploy-linux.ps1` | Omit `**/.build`, `**/__pycache__`, and test directories from deploy bundle |
| `--no-same-owner --no-same-permissions` on extract | Avoid utime/ownership failures on staging extract |
| `remove_tree()` with sudo fallback | Remove root-owned stale dirs via `~/.emic-deploy-sudo` when needed |
| Preserve `~/energy-monitoring/.env` | No config/data loss during code swap |
| `scripts/test_deploy_archive.ps1` (new) | Regression: archive must not contain `.build`; required paths present; SHA-256 valid |

### Recurrence detection / prevention

- **Local:** `scripts/test_deploy_archive.ps1` fails if `.build` or required paths missing from archive.
- **Remote:** `deploy-linux-extract.sh` verifies SHA-256 before extract; validates required files in staging; exits non-zero on any failure (no `|| true`, no silent skip).
- **Deploy bundle:** test directories excluded so fixture `.build` dirs cannot re-enter production archives.
- **Activation:** extract to `$HOME/energy-monitoring-staging-$$` first; only swap after validation.

---

## Deployment evidence

| Step | Result |
|------|--------|
| Local archive created | PASS |
| Local SHA-256 logged | PASS |
| Remote upload | PASS |
| Remote SHA-256 match | PASS |
| Staging extract | PASS |
| Content validation | PASS |
| Atomic activate/swap | PASS |
| Docker rebuild + restart | PASS |
| Post-deploy health | PASS |
| Rollback path preserved | PASS (previous release tree replaced atomically; `.env` preserved) |

---

## SPRINT D.5 PRODUCTION CLOSURE

### DEPLOY

| Criterion | Result |
|-----------|--------|
| Remote extract root cause | **PASS** (documented above) |
| Archive integrity verification | **PASS** (SHA-256 local + remote) |
| Remote extract | **PASS** |
| Deployment | **PASS** (`deploy-linux.ps1`) |
| Rollback safety | **PASS** (staging + `.env` preserve) |

### STORE PROD

| Criterion | Result |
|-----------|--------|
| Store UI loads | **PASS** (`/config/modules-devices/store` → 200, shell markers present) |
| Store catalog API | **PASS** (21 modules) |
| Admin auth | **PASS** (anonymous → 401) |

| Discover | **PASS** |
| Search | **PASS** (`charge` → matches; `zzznomatch999` → 0) |
| Categories | **PASS** (`EV Charging` filter → 1) |
| Filters | **PASS** (official, installed, control-capable) |

| Module detail | **PASS** (`integration.chargeamps` OFFICIAL, capabilities present) |
| Publisher detail | **PASS** (`emic` publisher, 21 modules) |
| Installed view | **PASS** (21 installed built-in/internal modules) |
| Updates view | **PASS** (empty state: 0 updates available) |
| Security Center | **PASS** (metadata_health=healthy, revoked publishers tracked) |

| Preflight | **PASS** (`integration.heartbeat` → ALLOW) |
| Preflight non-mutating | **PASS** (no install side effects; local test matrix) |

### POLICY PROD / DRY-RUN

| Criterion | Result |
|-----------|--------|
| OFFICIAL | **PASS** (preflight ALLOW on heartbeat) |
| COMMUNITY deny | **PASS** (0 community modules in trusted prod catalog; deny matrix in `test_module_store_catalog_api.py`) |
| REVOKED deny | **PASS** (revoked publishers in security center; 0 revoked modules in discover) |
| Control runtime blocked | **PASS** (`runtime_blocked=True`; control-capable built-in shows INSTALLED not RUN) |
| CRITICAL advisory deny | **N/A justified** (no active CRITICAL advisories in prod; fixture coverage in local tests) |
| Ownership mismatch deny | **N/A justified** (safe fixture depth partial per Sprint D scope) |

### SECURITY

| Criterion | Result |
|-----------|--------|
| Trusted catalog only | **PASS** (built-in + configured sources; no arbitrary public source enabled) |
| Sanitized content path | **PASS** (StoreCatalogService projection; XSS matrix in local tests) |
| No runtime side effects | **PASS** (preflight/read-only acceptance; no new runtime processes) |

### CORE

| Criterion | Result |
|-----------|--------|
| Core EMIC unaffected | **PASS** (dashboard 200; prod health PASS) |
| Prod health | **PASS** (`verify-prod-health.ps1`) |
| Prod runtime consistency | **PASS** (`verify-prod-runtime-consistency.ps1 -Strict`) |
| Prod logs | **PASS** (no ERROR/Traceback after Store use; expected 404s only from mistaken route probes) |

### SAFETY FLAGS

| Criterion | Result |
|-----------|--------|
| THIRD_PARTY_RUNTIME_ENABLED=false | **PASS** (docker exec + runtime API) |
| CONTROL_ISOLATION_GATE_OPEN=false | **PASS** (docker exec + code constant) |
| No third-party runtime running | **PASS** (runtime list empty, blocked flag set) |

### REGRESSION

| Criterion | Result |
|-----------|--------|
| Store backend tests | **PASS** (19 passed) |
| Store frontend tests | **PASS** (9 passed) |
| Deploy archive validation | **PASS** (`test_deploy_archive.ps1`) |
| Full regression | **PASS** (1749 Python + 743 frontend) |

---

## Scripts added/updated

| Script | Role |
|--------|------|
| `scripts/deploy-linux-extract.sh` | Atomic staging extract + hash verify |
| `scripts/deploy-linux.ps1` | Excludes test artifacts; invokes extract script |
| `scripts/test_deploy_archive.ps1` | Archive integrity regression |
| `scripts/verify-prod-store-acceptance.ps1` | Production Store smoke (18 checks) |

---

## Known limitations (carry-forward)

- SBOM/advisory detail remains summary-level (Sprint D PARTIAL accepted)
- No auto-update (by design)
- No non-admin Store browsing (by design)
- CRITICAL advisory / ownership mismatch fixture depth partial (local tests only)

---

## Blockers

**None.**

---

## Next step

1. **Sprint D targeted verification** (formal sign-off on acceptance table)
2. **Sprint E — Real External Module / SDK Validation** (Sensibo or similar; only after Sprint D production-verified)

---

**Status:** READY FOR SPRINT D VERIFICATION
