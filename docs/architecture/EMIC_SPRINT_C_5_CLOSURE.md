# EMIC Sprint C.5 — Runtime Isolation Closure

**Date:** 2026-09-08  
**Scope:** Close BLOCKER/HIGH/security-relevant MEDIUM findings from Sprint C Hard Security Verification  
**Authoritative prior verdict:** `NO-GO FOR THIRD-PARTY RUNTIME PILOT` ([EMIC_SPRINT_C_HARD_SECURITY_VERIFICATION.md](./EMIC_SPRINT_C_HARD_SECURITY_VERIFICATION.md))

This document does **not** declare pilot GO. It reports closure progress toward **re-verification readiness**.

---

## Finding closure

| ID | Status | Notes |
|----|--------|-------|
| F-01 | **OPEN** | Production Alembic head still `068_marketplace_distribution_supply_chain`; `069_isolated_module_runtime` not applied on `192.168.50.54` |
| F-02 | **OPEN** | Mandatory Linux bwrap adversarial matrix not executed in this environment (Windows dev host; 7 integration tests skipped) |
| F-03 | **OPEN** | `scripts/sprint-c-prod-acceptance.ps1` failed: migration 069, collector bwrap/bootstrap (docker/sudo), `EMIC_ADMIN_TOKEN` unset |
| F-04 | regression **PASS** | Fail-closed sandbox preserved; `test_sandbox_fail_closed.py` |
| F-05 | regression **PASS** | Control gate + governance at runtime start preserved |
| F-06 | regression **PASS** | `GetSecret` / `NetworkRequest` RPC wired |
| F-07 | regression **PASS** | Device safe-state revoke on stop/crash |
| F-08 | regression **PASS** | Minimal bwrap bind matrix (no `--ro-bind / /`) |
| F-09 | **OPEN** (hardened) | Added `--rlimit CPU`, disk quota enforcement in supervisor, config knobs; **Linux abuse probes not executed** |
| F-10 | **CLOSED** | `RuntimeSupervisor`: heartbeat miss → DEGRADED → stop → bounded restart → crash-loop quarantine; wired via `manager.supervise_tick()` |
| F-11 | **CLOSED** | `RuntimeSecurityMonitor`: publisher/module revocation + CRITICAL advisory → stop/quarantine |
| F-12 | **CLOSED** | Network broker redirect validation + DNS rebinding via Sprint B `validate_artifact_url`; E2E tests in `test_network_broker_e2e.py` |
| F-13 | **CLOSED** | Explicit `AcquireControlLease` / `RenewControlLease`; command denied without active lease |

---

## Code changes (Sprint C.5)

| Area | Change |
|------|--------|
| Supervisor | Heartbeat tracking, crash detection, disk quota, exponential backoff restart, quarantine |
| Security monitor | Revocation scan via `RevocationReader.find_active_revocation`; CRITICAL advisory via trust cache |
| Device broker | No auto-grant on expiry; lease keyed by `(runtime, site, device, capability)` |
| RPC gateway | `AcquireControlLease`, `RenewControlLease`; heartbeat persists `last_heartbeat_at` |
| Network broker | Redirect chain validation; `network.local` denied; reuse Sprint B URL policy |
| Config | `ISOLATED_RUNTIME_RESTART_BACKOFF_SECONDS`, `CONTROL_LEASE_TTL`, `DATA_QUOTA_MB`, `CPU_TIME_LIMIT` |
| bwrap | `--rlimit CPU` added alongside AS/NPROC/NOFILE |
| Prod acceptance | Try non-sudo docker first; control gate + anonymous denial checks |

---

## Acceptance matrix

### PRODUCTION

| Check | Result |
|-------|--------|
| Migration 069 | **FAIL** — prod at `068` |
| Sprint C deployed | **FAIL** — migration + acceptance blockers |
| bwrap present in prod | **FAIL** — collector probe blocked (docker/sudo) |
| runtime bootstrap present | **FAIL** — collector probe blocked |
| runtime low-privilege identity | **NOT VERIFIED** — Linux prod probe pending |
| THIRD_PARTY_RUNTIME_ENABLED=false | **PASS** |
| CONTROL_ISOLATION_GATE_OPEN=false | **PASS** (env empty/false) |
| Prod acceptance | **FAIL** |
| Prod health | **NOT RUN** |
| Prod runtime consistency | **NOT RUN** |
| Prod logs | **NOT RUN** |

### SANDBOX (Linux mandatory — not run here)

| Check | Result |
|-------|--------|
| Fail-closed | **PASS** (code + Windows unit tests) |
| No root runtime | **SKIP** — Linux integration |
| NoNewPrivileges | **SKIP** — Linux integration |
| Capabilities dropped | **SKIP** — Linux integration |
| Host filesystem denied | **SKIP** — Linux integration |
| Host secrets denied | **SKIP** — Linux integration |
| Cross-module files denied | **NOT RUN** |
| Package read-only | **SKIP** — Linux integration |
| Private temp | **PASS** (code) |
| Docker socket denied | **SKIP** — Linux integration |
| Host process inspection denied | **NOT RUN** |

### NETWORK

| Check | Result |
|-------|--------|
| Direct localhost/LAN/Internet/DNS denied | **SKIP** — Linux integration |
| Network broker | **PASS** — unit + RPC permission tests |
| SSRF | **PASS** — Sprint B url_policy reused |
| Redirect→private | **PASS** — `test_network_broker_e2e.py` |
| DNS rebinding | **PASS** — mocked resolution test |

### DATA / SECRETS

| Check | Result |
|-------|--------|
| Secret permission enforcement | **PASS** |
| Cross-module / cross-site secret | **PASS** |
| DB/Redis denied from sandbox | **SKIP** — Linux integration |

### RESOURCE CONTAINMENT

| Check | Result |
|-------|--------|
| CPU enforced | **PARTIAL** — bwrap `--rlimit CPU`; no cgroup proof |
| Memory / process / FD limits | **PARTIAL** — bwrap rlimits; abuse tests not run on Linux |
| Disk bounded | **PASS** — supervisor quota check (unit path) |
| CPU/memory/fork/FD abuse contained | **NOT RUN** — Linux integration |

### LIFECYCLE

| Check | Result |
|-------|--------|
| Heartbeat supervisor | **PASS** — `test_runtime_supervisor.py` |
| Hung runtime termination | **PASS** (unit) |
| Bounded restart / backoff / quarantine | **PASS** (unit) |
| Old token invalid after restart | **PASS** — session revoke on restart path |

### REVOCATION

| Check | Result |
|-------|--------|
| Publisher/module revocation stop | **PASS** (code; integration test pending) |
| Critical advisory transition | **PASS** (code) |
| Advisory R-3 | **PASS** — existing Sprint B tests |

### DEVICE CONTROL

| Check | Result |
|-------|--------|
| Explicit lease acquisition | **PASS** — `test_control_leases.py` |
| No automatic lease re-grant | **PASS** |
| Lease renewal authorization | **PASS** |
| Safe-state E2E | **PASS** — synthetic device unit tests |

### LINUX HARD SECURITY

| Check | Result |
|-------|--------|
| Production-equivalent Linux suite | **FAIL** — not executed |
| Real OS controls exercised | **FAIL** |
| 0 mandatory skips | **FAIL** — 7 skipped on Windows |

### REGRESSION

| Suite | Result |
|-------|--------|
| Full Python (`test-windows.ps1`) | **PASS** — 1668 passed, 13 skipped |
| Frontend (Vitest) | **PASS** — 734 passed |
| Isolation package | **PASS** — 39 passed, 7 skipped (Linux mandatory) |
| Architecture guards | **PASS** |

---

## Linux hard-security test counts (Windows host)

```text
collected:  46 (isolation/)
passed:     39
failed:     0
skipped:    7 (mandatory Linux @pytest.mark.integration)
```

**Required for re-verification:** `failed = 0`, `mandatory skipped = 0` on production-equivalent Linux.

---

## Production gates (verified remotely where possible)

```text
THIRD_PARTY_RUNTIME_ENABLED=false   PASS
CONTROL_ISOLATION_GATE_OPEN=false   PASS (unset/false in backend container)
```

Migration 069, bwrap/bootstrap, and authenticated runtime API checks remain **FAIL** until deploy credentials and admin token are available.

---

## Remaining work before re-verification

1. Apply migration `069_isolated_module_runtime` on PostgreSQL staging then production `192.168.50.54`.
2. Deploy Sprint C.5 collector image with bwrap + bootstrap; verify UID/GID 10001 inside running container.
3. Run full Linux adversarial matrix (`test_adversarial_matrix.py` + resource abuse probes) on production-equivalent Linux — **0 mandatory skips**.
4. Complete `scripts/sprint-c-prod-acceptance.ps1` with `EMIC_ADMIN_TOKEN`, docker access, post-deploy health/consistency scripts.
5. Run resource abuse scenarios (CPU/memory/fork/FD) on controlled Linux environment.

---

## Final line

```text
NOT READY FOR SPRINT C HARD SECURITY RE-VERIFICATION
```

Blockers F-01, F-02, F-03 remain open. F-09 Linux experimental proof pending. Independent re-verification must execute the Linux matrix and prod acceptance before issuing GO/NO-GO for pilot.
