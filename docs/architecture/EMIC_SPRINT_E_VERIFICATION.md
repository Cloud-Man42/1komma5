# SPRINT E TARGETED VERIFICATION

**Date:** 2026-09-09  
**Module:** `integration.sensibo` (Sensibo Climate, read-only)  
**Production host:** `192.168.50.54`  
**Site under test:** `akarp` (loaded from API; not hard-coded in tests)

---

## Final verdict

**SPRINT E NOT VERIFIED**

---

## Executive summary

Local/CI implementation evidence is strong: package identity, read-only client, exact runtime authorization model, generic climate path, Store fixtures, and **1727 Python / 747 frontend** regression tests pass on Windows.

Production platform code was deployed and migrated to **`072_sensibo_site_config`**. The generic climate API is live (`GET /api/sites/akarp/climate/devices` → 200, empty devices). Core prod health checks pass.

Verification **cannot close** because:

1. **Linux isolated Sensibo worker E2E** was not executed (Windows dev host; Linux bwrap tests skip; no Sensibo worker lifecycle test on Linux with `failed=0, skipped=0`).
2. **Production Sensibo E2E** is incomplete: Store catalog lacks `integration.sensibo`, no credential configured, no runtime authorization grant, no isolated runtime started, no live Sensibo readings in API/UI.

---

## Global safety state (production, post-deploy)

| Check | Evidence | Result |
|-------|----------|--------|
| `THIRD_PARTY_RUNTIME_ENABLED=false` | `sprint-e-sensibo-acceptance.ps1`: `third_party_runtime_enabled stays false - value=False` | **PASS** |
| `CONTROL_ISOLATION_GATE_OPEN=false` | Code: `ModuleInstallPolicyEngine.CONTROL_ISOLATION_GATE_OPEN = False` (`policy_engine.py`); unchanged | **PASS** |
| Runtime globally blocked without grant | `GET /api/modules/runtime` → `runtime_blocked=True` | **PASS** (expected) |

Values were not toggled during verification.

---

## Exact runtime authorization model (code inspection)

| Field | Implemented | Wildcards |
|-------|-------------|-----------|
| `module_id` | Yes (`RuntimeAuthorizationRepository.find_valid`) | No |
| `version` | Yes | No |
| `artifact_sha256` | Yes (lowercased) | No |
| `publisher_id` | Yes | No |
| `site_id` | Yes | No |

Local tests: `packages/energy-core/tests/platform/isolation/test_sensibo_authorization.py` (2 tests, production-env spawn gate).

Grant API/UI: `backend/app/api/module_runtime.py`, `RuntimeIsolationPanel.tsx`.

---

## Sensibo package identity (fixture artifact)

| Field | Value |
|-------|-------|
| `module_id` | `integration.sensibo` |
| `version` | `1.0.0` |
| `publisher_id` | `emic-official` |
| `artifact_sha256` | `eb540352a4ac8827851bd55a9ce920e561c7277d5567f0f6e91f8384b3fb9f1c` |
| Signature | Present (`integrity/signature.json` in `.emicpkg`) |
| `network_hosts` | `["home.sensibo.com"]` |
| Capabilities | Read-only `hvac.read_*` only |
| SBOM | `sbom_ref: embedded` in Store fixture catalog |

**Production Store:** `GET /api/modules/store/integration.sensibo` → **404** (catalog not published on prod). Search `?search=sensibo` → `total=0`.

---

## Standalone module architecture

Inspected `modules/sensibo/module/` (runtime code, excluding `build_emicpkg.py`):

| Requirement | Result |
|-------------|--------|
| No `energy_core` / `backend` / `sqlalchemy` imports | **PASS** (`backend/tests/test_sensibo_module.py`) |
| No direct Redis / PackageInstaller / ModuleOrchestrator | **PASS** |
| Core Sensibo-specific runtime logic | **PASS** (none in Core runtime paths) |

Core contains **generic** onboarding handler (`SensiboOnboardHandler` in `module_onboarding.py`) using Network Broker — acceptable per Sprint E design (broker-backed probe, not raw vendor HTTP in API layer).

---

## Read-only client

`sensibo_client.py`: `ALLOWED_METHODS = frozenset({"GET", "HEAD"})`; tick loop blocks non-GET in `module.py`.

| Check | Result |
|-------|--------|
| GET/read only in runtime client | **PASS** |
| POST/PUT/PATCH/DELETE in module tree | **PASS** (none) |

Failure-mode tests: `backend/tests/test_sensibo_module.py` (auth failure, normalization).

---

## Control / community / revoked regression (local)

| Scenario | Test | Result |
|----------|------|--------|
| Control gate closed → RUN DENY | `test_control_gate_blocks_without_isolation_open` | **PASS** |
| COMMUNITY → policy DENY | `test_store_community_denied_in_production` | **PASS** |
| Revoked publisher → DENY/REVOKED | `test_store_revoked_publisher` | **PASS** |

Control-capable Sensibo manifest variant: **not constructed** (not required for read-only module; control gate regression covered by existing demo/control fixtures).

---

## Linux isolated runtime E2E (Sensibo worker)

| Requirement | Result |
|-------------|--------|
| Real isolated Sensibo process on Linux | **NOT RUN** |
| Low-privilege uid/gid recorded | **NOT RUN** |
| Network/secret broker via runtime RPC | **NOT RUN** (Sensibo path) |
| `PublishReadings` → climate store | **NOT RUN** (prod/live) |
| Sprint E Linux tests `failed=0, skipped=0` | **FAIL** — 50 isolation tests skip on `win32`; prod backend image has no pytest |

Generic Linux isolation suite exists (`test_linux_*`) but was **not executed** in this verification session on Linux hardware.

---

## Network / secret broker (local non-Linux)

| Check | Tests | Result |
|-------|-------|--------|
| Broker contracts | `test_brokers.py`, `test_network_broker.py` | **PASS** |
| Cross-site deny | `test_cross_site.py` (in suite) | **PASS** (via regression) |
| Sensibo host allow | Onboarding handler uses `home.sensibo.com` only | **PASS** (code) |
| Arbitrary host deny | Existing Sprint C matrix tests | **PASS** (local, not re-run on Linux Sensibo path) |

---

## Production deployment

| Step | Result |
|------|--------|
| `deploy-linux.ps1` upload/extract | **PASS** (archive activated) |
| Remote `docker compose build/up` | **PASS** (manual `sudo -S` after script sudo failure) |
| Alembic head | **`072_sensibo_site_config`** (was `069` pre-deploy) |
| Climate API | **PASS** — `GET /api/sites/akarp/climate/devices` → 200 |
| `verify-prod-health.ps1` | **PASS** (snapshot, dashboard, Mercedes, Charge Amps, etc.) |
| `verify-prod-runtime-consistency.ps1 -Strict` | **PASS** |

---

## Production Store / install / config (incomplete)

| Step | Result |
|------|--------|
| Store lists `integration.sensibo` | **FAIL** — 404 |
| Preflight ALLOW | **FAIL** — 404 |
| Install through Store | **NOT DONE** |
| Credential configured | **FAIL** — `credential_configured=false` |
| Connectivity test (live Sensibo) | **NOT DONE** |
| Device discovery | **NOT DONE** |
| Runtime authorization grant | **FAIL** — count=0 |
| Start authorized runtime | **NOT DONE** |
| Live climate readings | **FAIL** — `devices=[]` |

`sprint-e-sensibo-acceptance.ps1` (2026-09-09): **3/6 checks failed** (store detail, preflight, authorization).

---

## Real Sensibo read E2E

**NOT VERIFIED**

Chain `Sensibo cloud → Network Broker → isolated module → PublishReadings → climate API/UI` was **not observed** with live data on production.

No Sensibo credential was configured during this session (credential never read, logged, or printed).

---

## Credential leak scan

| Surface | Result |
|---------|--------|
| Verification output / logs | **0 leaks** (token redacted; no API key material handled) |
| API responses inspected | No secret values in climate/external-config responses |

Full prod log grep for Sensibo runtime cycles: **not performed** (runtime never started).

---

## Full regression (local)

| Suite | Count |
|-------|-------|
| Python (`pytest`) | **1727 passed, 50 skipped**, 15 warnings |
| Sprint E focused | **46 passed** |
| Frontend (prior run post-RuntimeIsolationPanel fix) | **747 passed** |

Linux-skipped tests (50) include Sprint C/E isolation E2E requiring bwrap.

---

## SDK validation (Section 66)

| Question | Answer |
|----------|--------|
| Vendor-specific Core code required? | **NO** (generic climate + onboarding handler pattern) |
| Internal EMIC imports in module? | **NO** |
| Undocumented runtime internals? | **NO** |
| Direct network from module? | **NO** |
| Direct DB/Redis? | **NO** |
| Plaintext secrets in module? | **NO** |

---

## SDK friction

| Item | Severity |
|------|----------|
| Linux Sensibo worker E2E test missing in repo | **HIGH** — blocks automated Sprint E closure on CI/Linux |
| Prod marketplace catalog must include `integration.sensibo` release | **HIGH** — Store 404 blocks normal install path |
| `deploy-linux.ps1` remote sudo without `~/.emic-deploy-sudo` | **MEDIUM** — deploy script failed until manual `sudo -S` |
| SDK docs referenced as `docs/sdk/EMIC_*` — actual paths `docs/module-sdk/`, `docs/security/` | **LOW** (DX) |

---

## Blockers (open)

1. **Prod Store catalog** does not expose `integration.sensibo` (404).
2. **No production Sensibo credential / device config / runtime authorization** configured.
3. **No live Sensibo read** reaching climate API/UI.
4. **Linux isolated Sensibo worker E2E** not executed with `failed=0, skipped=0`.

---

## Acceptance summary

| Area | Result |
|------|--------|
| Standalone external module | **PASS** (local) |
| No vendor Core logic | **PASS** |
| No internal imports | **PASS** |
| Generic SDK only | **PASS** |
| `.emicpkg` | **PASS** (fixture) |
| Signature | **PASS** (fixture) |
| Ownership | **PASS** (fixture/tests) |
| SBOM/security | **PASS** (fixture) |
| Store preflight | **PASS** (local) / **FAIL** (prod) |
| Exact per-module authorization | **PASS** (code + local tests) |
| Global runtime remains disabled | **PASS** (prod) |
| Control gate remains closed | **PASS** |
| Linux isolated Sensibo runtime | **FAIL** |
| Low privilege | **NOT RUN** |
| Artifact/site binding | **PASS** (local auth tests) |
| Direct network denied | **NOT RUN** (Sensibo Linux) |
| Sensibo broker network allowed | **NOT RUN** (live) |
| Arbitrary network denied | **PASS** (local Sprint C tests) |
| Redirect/DNS security | **NOT RUN** (Sensibo path) |
| Secret Broker | **PASS** (local) |
| Credential scope | **PASS** (code) |
| No credential leakage | **PASS** (session) |
| Real Sensibo authentication | **FAIL** |
| Device discovery | **FAIL** |
| Temperature / humidity / state / status | **FAIL** |
| Target temperature | **N/A** |
| Generic climate publish | **FAIL** (prod) |
| Climate UI | **FAIL** (no data) |
| GET/read-only API | **PASS** (client) |
| No Sensibo write calls | **PASS** (static + tests) |
| Control capability denied | **PASS** |
| Invalid credential / timeout / 429 / 5xx / malformed / stale / recovery | **PARTIAL** (unit tests only) |
| Site isolation | **PASS** (local cross-site tests) |
| DB/Redis denied | **PASS** (Sprint C local) |
| Filesystem isolation | **NOT RUN** (Sensibo Linux) |
| Heartbeat/resource stability | **PASS** (prod health) |
| Clean stop / old token / restart / authority removed | **NOT RUN** (prod) |
| Other unapproved module still denied | **PASS** (authorization gate local) |
| Store state (prod) | **FAIL** |
| Security display (prod) | **FAIL** |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |
| Core EMIC unaffected | **PASS** |
| Prod logs (Sensibo runtime) | **NOT RUN** |
| Full regression | **PASS** (local; 50 Linux skips) |

---

## Final security answers

| Question | Answer |
|----------|--------|
| Vendor-specific Core changes? | **NO** |
| Internal EMIC imports in module? | **NO** |
| Direct network? | **NO** |
| Direct DB/Redis? | **NO** |
| Credential outside Secret Broker? | **NO** (design); **not exercised on prod** |
| Sensibo write/control operation? | **NO** (code/tests) |
| General third-party runtime enabled? | **NO** (prod verified) |
| Control gate opened? | **NO** |

---

## Next phase (if/when verified)

Recommend: **SPRINT F — THIRD-PARTY CONTROL MODULE SECURITY GATE** (not in scope for this task).

---

## Operator actions required to reach VERIFIED

1. Publish `integration.sensibo@1.0.0` to production marketplace trust cache / Store catalog.
2. Install via Store on target site (`akarp` or chosen site from API).
3. Configure Sensibo API key + device selection via wizard or external-config API.
4. Grant exact runtime authorization (module, version, sha256, publisher, site).
5. Start runtime; confirm climate readings in API/UI.
6. Run Linux isolated Sensibo E2E on bwrap host (add/execute test suite; `failed=0, skipped=0`).
7. Re-run `sprint-e-sensibo-acceptance.ps1` and prod log review.

---

**SPRINT E NOT VERIFIED**
