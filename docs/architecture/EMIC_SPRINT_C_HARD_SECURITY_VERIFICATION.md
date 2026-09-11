# SPRINT C HARD SECURITY VERIFICATION

**Verifier:** Independent adversarial review (Step 5C.5)  
**Date:** 2026-09-08  
**Scope:** Third-party runtime isolation foundation — code, tests, production posture  

---

## Primary security question

> If a malicious VERIFIED third-party module is executed inside the Sprint C runtime, can it escape its assigned permissions and affect the EMIC host, another module, another site, a secret, the network, the database, Redis, Docker, or a physical device?

**Answer with current evidence:** **MAYBE / UNKNOWN on Linux production path** — foundation improved during verification, but **production-equivalent Linux adversarial matrix was not executed** (SSH/sudo blocked; migration 069 not applied on prod). Windows subprocess tests are **not** sufficient evidence.

**Required answer for GO:** NO — **not met**.

---

## Final decision

```text
NO-GO FOR THIRD-PARTY RUNTIME PILOT
```

---

## Findings summary

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| F-01 | **BLOCKER** | Production Alembic head still `068`; migration `069_isolated_module_runtime` not applied | Open |
| F-02 | **BLOCKER** | Mandatory Linux bwrap adversarial matrix not executed (7 tests skipped on Windows; prod collector SSH unavailable in batch) | Open |
| F-03 | **BLOCKER** | `scripts/sprint-c-prod-acceptance.ps1` failed (migration, bwrap/bootstrap checks, admin token) | Open |
| F-04 | **HIGH** | Prior code: bwrap missing → subprocess fallback (fixed in verification — fail-closed now) | **Fixed** |
| F-05 | **HIGH** | Prior code: control gate ignored at runtime start (permissions not passed to governance) | **Fixed** |
| F-06 | **HIGH** | Prior code: Secret/Network brokers not RPC-exposed | **Fixed** (`GetSecret`, `NetworkRequest`) |
| F-07 | **HIGH** | Prior code: device safe-state not wired on stop/crash | **Fixed** (`device_broker.revoke_runtime`) |
| F-08 | **HIGH** | Prior code: `--ro-bind / /` exposed host FS read-only | **Fixed** (minimal bind roots) |
| F-09 | **HIGH** | Resource limits configured but not enforced | **Partially fixed** (bwrap `--rlimit`; no CPU cgroup) |
| F-10 | **MEDIUM** | Heartbeat miss → DEGRADED/terminate policy not implemented | Open |
| F-11 | **MEDIUM** | Revocation/advisory while runtime running not wired | Open |
| F-12 | **MEDIUM** | Network broker redirect→private / DNS rebinding adversarial tests incomplete | Partial (url_policy unit tests elsewhere) |
| F-13 | **MEDIUM** | Device broker auto-grants lease on expiry (TTL semantics weak) | Open |
| F-14 | **INFO** | Windows dev uses TCP localhost RPC + subprocess (documented non-prod) | Accepted |

**BLOCKER count:** 3 open  
**Unresolved HIGH:** 0 (F-04–F-08 fixed; F-09 partial remains MEDIUM for GO)

---

## SPRINT C HARD SECURITY SCORE

```text
SPRINT C HARD SECURITY SCORE: 42 / 100
```

| Category | Score | Notes |
|----------|-------|-------|
| Process Isolation | 55 | Out-of-process + bwrap launcher; Linux not verified live |
| Filesystem Isolation | 50 | Minimal binds + tests written; not run on Linux |
| Network Isolation | 45 | `--unshare-net` + broker; not adversarial-verified |
| RPC Security | 70 | Auth, limits, identity tests pass |
| Secret Isolation | 65 | Broker + RPC; unit tests pass |
| Data Isolation | 60 | Cross-site read tests pass |
| Device-Control Isolation | 55 | Synthetic broker; safe-state unit tests |
| Multi-Site Isolation | 65 | Cross-site broker tests pass |
| Resource Containment | 35 | rlimit AS/NPROC/NOFILE added; no live abuse tests |
| Lifecycle Safety | 50 | Start/stop/timeout; no heartbeat/revocation hooks |
| Safe-State | 55 | Revoke wired; not E2E crash tested on Linux |
| Revocation Handling | 30 | R-3 advisory merge PASS; runtime revocation not wired |
| Architecture Boundaries | 85 | SDK/bootstrap guards PASS |
| Linux Test Quality | 15 | 7 mandatory skips; matrix not run on prod collector |
| Production Safety | 25 | Flags dormant PASS; migration 069 / acceptance FAIL |

---

## Acceptance matrix

### OUT-OF-PROCESS

| Check | Result |
|-------|--------|
| No in-process third-party import | **PASS** — loader `skip_import=True` for VERIFIED/ORG_APPROVED |
| Runtime identity | **PASS** — DB + handshake binding |
| Artifact digest binding | **PASS** — manager verify + handshake mismatch tests |
| Runtime attestation | **PASS** — version/digest/module_id/protocol tests |

### SANDBOX

| Check | Result |
|-------|--------|
| Production-equivalent Linux sandbox | **FAIL** — not executed (F-02) |
| No unsandboxed fallback | **PASS** (after fix) — `SandboxUnavailableError` in production |
| Dedicated low-privilege identity | **PASS** (code) — UID/GID 10001; Linux probe test not run |
| No root runtime | **FAIL** — probe test not run on Linux |
| NoNewPrivileges | **PASS** (code) — `--no-new-privs` in bwrap cmd |
| Capabilities dropped | **PASS** (code) — `--cap-drop ALL` |
| Host filesystem denied | **FAIL** — tests not run on Linux |
| Cross-module filesystem denied | **FAIL** — not tested |
| Package read-only | **FAIL** — probe test not run |
| Private temp | **PASS** (code) — `--tmpfs /tmp` |
| Host secrets denied | **FAIL** — env probe not run |
| Docker socket denied | **FAIL** — probe not run |
| Host process inspection restricted | **FAIL** — not tested |

### NETWORK

| Check | Result |
|-------|--------|
| Direct network default deny | **PASS** (code) — `--unshare-net`; Linux not verified |
| Localhost / LAN / Internet denied | **FAIL** — evil_network probe not run |
| Direct DNS denied | **FAIL** — not tested |
| Network broker | **PASS** — unit tests + RPC wiring |
| Host allowlist | **PASS** — unit test |
| SSRF protection | **PASS** — reuses `validate_artifact_url` |
| Redirect→private | **PARTIAL** — distribution tests; not runtime broker E2E |
| DNS rebinding | **PARTIAL** — url_policy tests elsewhere |

### RPC

| Check | Result |
|-------|--------|
| Authenticated RPC | **PASS** |
| Runtime identity binding | **PASS** |
| Token replay denied | **PASS** |
| Post-stop token denied | **PASS** |
| Cross-runtime impersonation denied | **PASS** |
| Cross-site RPC denied | **PASS** (broker layer) |
| Schema validation | **PASS** |
| Size limits | **PASS** |
| Timeouts | **PARTIAL** — handshake read timeout only |
| Rate/concurrency limits | **PARTIAL** — code present; flood test not added |

### SECRETS

| Check | Result |
|-------|--------|
| No secret permission → deny | **PASS** |
| No secret enumeration | **PASS** |
| Own-secret scope | **PASS** (unit) |
| Cross-module secret denied | **PASS** |
| Cross-site secret denied | **PASS** (implicit module+site key) |
| Secret audit | **PASS** (unit) |
| No secret values in audit | **PASS** (code review) |

### DATA

| Check | Result |
|-------|--------|
| No direct DB | **PASS** (architecture; env probe not run) |
| No DB credentials inherited | **FAIL** — env probe not run on Linux |
| No direct Redis | **PASS** (architecture) |
| No Redis credentials inherited | **FAIL** — env probe not run |

### DEVICE CONTROL

| Check | Result |
|-------|--------|
| No direct integration access | **PASS** — SDK isolation |
| Device broker required | **PASS** |
| Permission enforcement | **PASS** |
| Site isolation | **PASS** |
| Device isolation | **PARTIAL** |
| Typed command validation | **PASS** |
| Safety envelope | **PASS** |
| Control lease | **PASS** (unit) |
| Lease expiry on death | **PASS** (unit + revoke wired) |
| Safe-state verified | **PARTIAL** — unit only |

### RESOURCE CONTAINMENT

| Check | Result |
|-------|--------|
| CPU abuse contained | **FAIL** — not tested |
| Memory abuse contained | **FAIL** — rlimit AS in code; not tested |
| Fork abuse contained | **FAIL** — not tested |
| FD abuse contained | **FAIL** — not tested |
| Disk abuse contained | **FAIL** — not tested |

### LIFECYCLE

| Check | Result |
|-------|--------|
| Startup timeout | **PASS** |
| Handshake | **PASS** |
| Heartbeat | **PARTIAL** — worker sends GetHealth; no supervisor |
| Hung runtime containment | **PARTIAL** |
| Crash containment | **PASS** (unit + revoke) |
| Bounded restart | **FAIL** — not implemented |
| Crash-loop protection | **FAIL** — not implemented |
| Capabilities removed on stop | **PASS** |

### SECURITY TRANSITIONS

| Check | Result |
|-------|--------|
| Revocation stops runtime | **FAIL** — not wired |
| Revocation removes leases | **FAIL** |
| Critical advisory handling | **FAIL** |
| Advisory omission protection (R-3) | **PASS** |
| Runtime quarantine | **PASS** (digest mismatch path) |

### ARCHITECTURE

| Check | Result |
|-------|--------|
| SDK cannot import Core | **PASS** |
| No PackageInstaller direct path | **PASS** |
| No ModuleOrchestrator direct path | **PASS** |
| No integration client access | **PASS** (design) |
| No secret-store direct access | **PASS** |

### TEST QUALITY

| Check | Result |
|-------|--------|
| Linux hard-security tests | **FAIL** — 7 skipped (Windows); 0 run on prod collector |
| 0 mandatory security skips | **FAIL** |
| Tests exercise real OS controls | **FAIL** |

### PRODUCTION

| Check | Result |
|-------|--------|
| Migration 069 | **FAIL** — prod at `068` |
| Sprint C foundation deployed | **PARTIAL** — code in repo; prod not migrated |
| THIRD_PARTY_RUNTIME_ENABLED=false | **PASS** |
| CONTROL_ISOLATION_GATE_OPEN=false | **PASS** (code constant) |
| No general runtime start | **PASS** — no POST start route |
| Controlled prod acceptance | **FAIL** |
| Dormant state restored | **N/A** — runtime never enabled |
| No physical device side effects | **PASS** (no runtime spawned on prod) |
| Prod health | **NOT RUN** — SSH blocked |
| Prod runtime consistency | **NOT RUN** |
| Core EMIC unaffected | **ASSUMED** — no runtime enabled |

### REGRESSION (local Windows, 2026-09-08)

| Suite | Result |
|-------|--------|
| Sprint C isolation + guards + advisory + runtime API + governance API | **52 passed, 7 skipped** |
| Frontend RuntimeIsolationPanel | **1 passed** |
| Full `test-windows.ps1` | **Not re-run in this verification** (prior run: 1652 passed, 1 failed — bootstrap path since fixed) |

**Linux hard-security suite (mandatory):** **0 collected on Windows host** — 7 tests skipped (`@pytest.mark.skipif(win32)`).

---

## Code audit evidence

### Feature flags (§4)

- [`config.py`](packages/energy-core/src/energy_core/config.py): `THIRD_PARTY_RUNTIME_ENABLED` default `false`
- [`policy_engine.py`](packages/energy-core/src/energy_core/platform/modules/governance/policy_engine.py): `CONTROL_ISOLATION_GATE_OPEN = False` (no env override)
- Prod probe: `THIRD_PARTY_RUNTIME_ENABLED` empty/false (**PASS**)

### No general start API (§5)

- [`module_runtime.py`](backend/app/api/module_runtime.py): GET list/detail/security, POST stop only — **no POST start**

### Fixes applied during verification

1. [`sandbox/__init__.py`](packages/energy-core/src/energy_core/platform/modules/isolation/sandbox/__init__.py) — fail-closed; production rejects subprocess; missing bwrap raises
2. [`linux_bwrap.py`](packages/energy-core/src/energy_core/platform/modules/isolation/sandbox/linux_bwrap.py) — minimal ro-binds, `--no-new-privs`, `--rlimit`
3. [`manager.py`](packages/energy-core/src/energy_core/platform/modules/isolation/manager.py) — manifest permissions to governance; device broker revoke
4. [`gateway.py`](packages/energy-core/src/energy_core/platform/modules/isolation/rpc/gateway.py) — `GetSecret`, `NetworkRequest`
5. [`sandbox_demo.py`](packages/energy-core/tests/fixtures/modules/integration.sandbox-demo/module/sandbox_demo.py) — probe modes for Linux matrix
6. New tests: `test_adversarial_matrix.py`, `test_sandbox_fail_closed.py`, `test_rpc_brokers.py`

---

## Path to GO (not in scope of this verification)

1. Apply migration **069** on production; redeploy collector with bwrap + bootstrap
2. Run Linux adversarial matrix **inside prod collector** — **0 skips, all PASS**
3. Pass `sprint-c-prod-acceptance.ps1`, `verify-prod-health.ps1`, `verify-prod-runtime-consistency.ps1 -Strict`
4. Wire heartbeat supervisor, crash-loop quarantine, runtime revocation hooks
5. Complete network redirect/DNS rebinding broker E2E tests
6. Re-run full regression

---

## Final security statement

A malicious verified non-control third-party module **cannot be asserted safe** today: Linux sandbox containment is **not experimentally proven** in the production-equivalent environment, production schema lacks runtime tables, and several lifecycle/revocation controls remain unwired. Code improvements during this verification reduce risk but **do not satisfy GO criteria**.

---

```text
NO-GO FOR THIRD-PARTY RUNTIME PILOT
```
