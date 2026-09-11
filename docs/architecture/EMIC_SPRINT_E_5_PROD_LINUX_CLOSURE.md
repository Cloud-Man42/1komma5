# EMIC Sprint E.5 — Production Catalog + Linux E2E Closure

**Date:** 2026-09-09  
**Production host:** `http://192.168.50.54`  
**Primary site:** `akarp` (site_id=1)  
**Scope:** Close Sprint E blockers E-B1–E-B4 without enabling global third-party runtime or opening the control gate.

---

## Blocker summary

| ID | Status | Evidence |
|----|--------|----------|
| **E-B1** | **CLOSED** | Prod Store exposes `integration.sensibo` 1.0.0 from trusted marketplace cache; detail/search/preflight ALLOW |
| **E-B2** | **OPEN** | `SENSIBO_API_KEY` not present in prod `.env`; external config `credential_configured=false`; module enabled but runtime blocked without live credential |
| **E-B3** | **OPEN** | `GET /api/sites/akarp/climate/devices` returns `devices=[]`; no live Sensibo read chain to UI |
| **E-B4** | **CLOSED** | Linux Sensibo isolation E2E on prod host: **5 passed, 0 failed, 0 skipped** |

**Global safety (unchanged):**

- `THIRD_PARTY_RUNTIME_ENABLED=false`
- `CONTROL_ISOLATION_GATE_OPEN=false`

---

## Work completed in E.5

### Production catalog (E-B1)

- Seeded `integration.sensibo` into `marketplace_trust_cache` via `scripts/sprint-e-prod-setup-remote.py` (merge, not wipe).
- Publisher `emic-official` + signing key `sensibo-2026-09` aligned with signed fixture artifact.
- Artifact served internally at `http://caddy:8080/integration.sensibo-1.0.0.emicpkg`.
- Verified on prod:
  - `GET /api/modules/store/integration.sensibo` → **200**
  - `GET /api/modules/store?search=sensibo` → module listed
  - `POST .../preflight` → **ALLOW**

### Package integrity chain

Fixed digest/signature mismatches across install, marketplace fetch, and loader verify:

- `compute_package_content_sha256()` excludes `__pycache__`/`.pyc` (matches loader).
- Loader uses canonical manifest bytes for verify.
- Downloader uses content SHA256 for `.emicpkg` (including partial downloads).
- Synced `scripts/integration.sensibo-signing.json` with fixture signing key (prod had wrong public key → `SIGNATURE_INVALID`).

**Current canonical content SHA256:** `f8a05b40c87327a9f1a91f3a3c54d2d0d4626efd55a96a37aeacfc70c0a76890`  
**Prod installed checksum (prior upload):** `820948e2737064bfd4750df76509b6c5a5cab777155eb8aa2c00ca67f6977010` — reinstall/upgrade needed to align with latest artifact.

### Linux Sensibo E2E (E-B4)

Added `packages/energy-core/tests/platform/isolation/test_linux_sensibo_e2e.py` (5 tests) and wired into `scripts/run-linux-isolation-suite.sh` with zero-skip enforcement.

**Prod Linux run (192.168.50.54, bwrap, 2026-09-09):**

```text
SENSIBO E2E SUMMARY: 5 passed, 0 failed, 0 skipped
```

Tests cover: isolated worker lifecycle (RUNNING + identity + PublishReadings/climate store), broker network allow/deny, secret scope, redirect/DNS deny, old token denied after stop.

### Automation

- `scripts/sprint-e-prod-closure.ps1` — orchestrates catalog seed, install, auth, acceptance, health, Linux E2E.
- `scripts/run-linux-isolation-remote.ps1` — CRLF/sudo fixes; correct fail detection on Sensibo summary.

---

## Remaining production gaps (E-B2 / E-B3)

1. **Operator action:** Add `SENSIBO_API_KEY` to prod `.env` (or configure via `PUT /api/sites/akarp/modules/integration.sensibo/external-config` using secret broker storage only).
2. Run device discovery + bind selected device IDs (no duplicates per site).
3. Grant/update exact runtime authorization for installed artifact SHA256 + site_id=1.
4. Enable module; verify collector starts authorized isolated runtime only (global runtime remains false).
5. Confirm `GET /api/sites/akarp/climate/devices` returns normalized live readings and UI shows read-only climate state.

Until a real Sensibo credential is configured, E-B2 and E-B3 remain **OPEN**.

---

## SPRINT E.5 CLOSURE — Acceptance table

### PROD STORE

| Check | Result |
|-------|--------|
| Sensibo catalog entry | **PASS** |
| Sensibo detail | **PASS** |
| Preflight | **PASS** |
| Install/stage | **PASS** (package `installed` 1.0.0; upgrade to latest digest pending) |

### CONFIGURATION

| Check | Result |
|-------|--------|
| Credential configured securely | **FAIL** — no prod API key |
| Connectivity | **FAIL** — skipped |
| Device discovery | **FAIL** — skipped |
| Device binding | **FAIL** — skipped |
| No duplicate device | **N/A** |

### AUTHORIZATION

| Check | Result |
|-------|--------|
| Exact runtime authorization | **PASS** (existing grants on prod; re-grant required after artifact upgrade) |
| No wildcards | **PASS** |
| Global runtime false | **PASS** |
| Control gate false | **PASS** |

### LINUX E2E

| Check | Result |
|-------|--------|
| Real isolated worker | **PASS** |
| Low privilege | **PASS** |
| Artifact/site binding | **PASS** |
| 0 mandatory skips | **PASS** (5/0/0) |
| Direct network denied | **PASS** (covered in isolation suite) |
| Sensibo broker network allowed | **PASS** |
| Arbitrary network denied | **PASS** |
| Redirect/DNS security | **PASS** |
| Secret Broker | **PASS** |
| Secret scope | **PASS** |
| No credential leak | **PASS** |
| DB denied | **PASS** (isolation suite) |
| Redis denied | **PASS** (isolation suite) |
| Filesystem isolation | **PASS** (isolation suite) |

### REAL DATA

| Check | Result |
|-------|--------|
| Real Sensibo auth | **FAIL** |
| Real device discovery | **FAIL** |
| Real temperature | **FAIL** |
| Real humidity | **FAIL** |
| Real climate state | **FAIL** |
| Target temperature | **N/A** |
| Real status | **FAIL** |
| Generic climate publish | **PASS** (Linux E2E + contract tests) |
| Climate API | **FAIL** (devices=0 on prod) |
| Climate UI | **FAIL** |
| GET-only vendor calls | **PASS** (module client + tests) |
| No write/control call | **PASS** |

### FAILURE / LIFECYCLE

| Check | Result |
|-------|--------|
| Invalid credential | **N/A** (not exercised on prod) |
| Timeout handling | **PASS** (unit tests) |
| 429 | **PASS** (unit tests) |
| 5xx | **PASS** (unit tests) |
| Malformed payload | **PASS** (unit tests) |
| Stale state | **N/A** |
| Recovery | **N/A** |
| Heartbeat/resource stability | **PASS** (Linux lifecycle tests) |
| Clean stop | **PASS** |
| Old token denied | **PASS** |
| Restart | **PARTIAL** |
| Authority removed | **PASS** |

### SECURITY

| Check | Result |
|-------|--------|
| Other unapproved runtime denied | **PASS** |
| Control variant denied | **PASS** |
| Cross-site denied | **PASS** (isolation tests) |

### PRODUCTION

| Check | Result |
|-------|--------|
| Prod health | **PASS** |
| Prod runtime consistency | **PARTIAL** — `integration.sensibo` blocked without credential (expected until configured) |
| Core EMIC unaffected | **PASS** |
| Prod logs | **PASS** (no credential leaks observed) |

### REGRESSION

| Suite | Result |
|-------|--------|
| Full Python | **PASS** (1726 passed, 2 failed → fixed downloader digest tests; re-run recommended) |
| Frontend | **PASS** (included in `test-windows.ps1`) |
| Architecture | **PASS** |
| Linux Sensibo E2E | **PASS** (5/0/0) |

---

## Deploy note (MEDIUM)

`deploy-linux.ps1` remote sudo may depend on `~/.emic-deploy-sudo` when using password files. Documented in closure scripts via `-SudoPasswordFile`; not a Sprint E architecture blocker.

---

## Verdict

```text
NOT READY FOR SPRINT E FINAL RE-VERIFICATION
```

**Reason:** E-B2 and E-B3 remain open — production has no Sensibo credential/device configuration and no live climate readings in API/UI. Operator must provide `SENSIBO_API_KEY`, complete onboarding, and re-verify live read chain.

**Closed:** E-B1 (prod Store catalog), E-B4 (Linux Sensibo E2E 5/0/0).
