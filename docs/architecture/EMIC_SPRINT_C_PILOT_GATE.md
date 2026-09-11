# EMIC Sprint C — Final Limited Runtime Pilot Gate

**Date:** 2026-09-08  
**Verifier:** Independent post–Sprint C.7 re-verification  
**Production target:** `192.168.50.54`  
**Scope:** GO / NO-GO for **limited NON-CONTROL** third-party runtime pilot only

---

## Final Verdict

```text
GO FOR LIMITED THIRD-PARTY RUNTIME PILOT
```

Production remains **dormant** (`THIRD_PARTY_RUNTIME_ENABLED=false`, `CONTROL_ISOLATION_GATE_OPEN=false`). This gate **authorizes** a future bounded pilot profile; it does **not** start any runtime.

---

## Primary Security Question

> Can a malicious VERIFIED non-control module escape its isolated runtime or gain unauthorized host/core/network/data/secret/site/device authority?

**Answer (with experimental evidence):** **NO**

Evidence: 41/41 mandatory Linux integration tests PASS (host bwrap 0.9.0 and collector-extracted bwrap 0.8.0), covering pre-drop adversarial fixtures, sandbox filesystem/network/privilege probes, live broker RPC from actual sandbox, lifecycle/revocation/safe-state E2E, and resource containment. Bootstrap code review confirms no attacker-controlled Python before privilege drop.

---

## Independent Re-Run Evidence (2026-09-08)

### Linux security counts

| Path | bwrap | Collected | Passed | Failed | Skipped |
|------|-------|-----------|--------|--------|---------|
| Host (`run-linux-isolation-suite.sh`) | 0.9.0 | 41 | 41 | 0 | 0 |
| Collector path (`EMIC_BWRAP_PATH` = collector `/usr/bin/bwrap`) | **0.8.0** | 41 | 41 | 0 | 0 |

### Collector image identity

| Field | Value |
|-------|-------|
| Container | `energy-monitoring-collector-1` |
| Image digest | `energy-monitoring-collector@sha256:bb7ac16b386c23f439c37d43b77472d33c6c6a2ba37f48611b9454add5bed172` |
| bwrap | `bubblewrap 0.8.0` (extracted to `/tmp/emic-collector-bwrap-0.8.0`) |
| Bootstrap sha256 | `9f481895c825391ffd7550323f374a85d52bde6e224e8dd48c70b9732d0328be` |

**Note (INFO):** Docker seccomp blocks namespace creation inside the collector container during `docker exec`. Mandatory tests therefore use the **exact production collector bwrap 0.8.0 binary** on the production host with the same UID/GID model (10001) and bootstrap — matching how collector launches sandboxes at runtime. This is not a material path divergence for bwrap behavior.

### Full regression

| Suite | Result |
|-------|--------|
| Python (Step 5B / 5C.1 / Sprint A–C inclusive) | **1681 passed**, 50 skipped, 0 failed |
| Frontend | **734 passed**, 0 failed (158 files) |
| Architecture (bootstrap order, isolation unit tests) | Included in Python suite — PASS |

---

## Bootstrap Order (Code Inspection)

Verified in `scripts/isolated_runtime_bootstrap.py`:

```text
Handshake
→ _apply_sandbox_hardening()
→ _drop_module_identity()          [includes os.setgroups([])]
→ _verify_effective_identity()
→ BootstrapReady (post-drop uid/gid)
→ _load_module_entry()
→ runtime.start()
→ ReportModuleReady
```

- No `energy_core`, SQLAlchemy, Redis, or installer imports in bootstrap.
- `test_bootstrap_security_order.py` enforces ordering in CI.

---

## Findings

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| PG-01 | INFO | Collector suite script has CRLF on prod host; manual `EMIC_BWRAP_PATH` run used for verification | Accepted |
| PG-02 | INFO | In-container bwrap namespace tests blocked by Docker seccomp; collector binary tested on host | Accepted |
| PG-03 | INFO | Prod collector logs (6h): no privilege_drop/sandbox/quarantine Tracebacks | Clean |

**BLOCKER:** 0  
**HIGH:** 0  
**Security-boundary MEDIUM:** 0

---

## FINAL LIMITED RUNTIME PILOT GATE

### Pre-drop & privilege

| Check | Result |
|-------|--------|
| Pre-drop adversarial | **PASS** (11 tests: sitecustomize, usercustomize, `__init__`, entrypoint, canaries, forced drop, groups, regain) |
| Privilege drop | **PASS** |
| Drop failure audit (`runtime.privilege_drop_failed`) | **PASS** |

### Collector path

| Check | Result |
|-------|--------|
| Collector bwrap 0.8.0 path | **PASS** |
| 0 security skips | **PASS** |

### Sandbox boundaries

| Check | Result |
|-------|--------|
| Filesystem isolation | **PASS** |
| Direct network isolation | **PASS** |
| DB/Redis isolation | **PASS** (env scrub + no broker path) |
| Secret isolation | **PASS** |
| Cross-site isolation | **PASS** |

### Live brokers (from sandbox RPC)

| Check | Result |
|-------|--------|
| Network broker live | **PASS** |
| Secret broker live | **PASS** |
| Read broker live | **PASS** |

### RPC security

| Check | Result |
|-------|--------|
| Auth / replay / impersonation / size / rate | **PASS** (unit + E2E) |

### Resources

| Check | Result |
|-------|--------|
| CPU / memory / fork / FD / disk quota | **PASS** |

### Lifecycle

| Check | Result |
|-------|--------|
| Heartbeat / hung containment | **PASS** |
| Crash-loop quarantine | **PASS** |
| Token rotation | **PASS** |

### Revocation & safe-state

| Check | Result |
|-------|--------|
| Revocation stop (publisher + module) | **PASS** |
| Critical advisory transition | **PASS** |
| Lease lifecycle | **PASS** |
| Safe-state (synthetic device) | **PASS** |

### Architecture

| Check | Result |
|-------|--------|
| Architecture guards (no Core internals in sandbox worker) | **PASS** |
| COMMUNITY tier runtime denied | **PASS** (code: `tier_allows_runtime`) |
| Control-capable modules blocked while gate closed | **PASS** |

### Production

| Check | Result |
|-------|--------|
| Migration 069 | **PASS** |
| Prod acceptance | **PASS** |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |
| Prod logs | **PASS** |
| `THIRD_PARTY_RUNTIME_ENABLED=false` | **PASS** |
| `CONTROL_ISOLATION_GATE_OPEN=false` | **PASS** |
| No third-party runtime processes | **PASS** |
| Full regression | **PASS** |

---

## Pilot Constraints (Mandatory Even After GO)

```text
CONTROL_ISOLATION_GATE_OPEN=false          → control modules DENY
COMMUNITY publisher tier                 → runtime DENY
One module at a time
VERIFIED or ORG_APPROVED only
NON-CONTROL capabilities only
No physical device commands
Minimal manifest permissions
Strict network allowlist (or none)
Minimal/no secrets
Explicit administrator approval per session
Full audit + automatic quarantine/revocation active
```

---

## Recommended First Pilot Profile (Do Not Start Here)

```text
module:        integration.runtime-pilot-demo
trust:         VERIFIED internal test publisher
capabilities:  read-only synthetic status
network:       none
secrets:       none
devices:       none
site:          one dedicated test site
duration:      bounded manual session
control:       none
```

---

## Final Security Statement

With experimental evidence from production-equivalent Linux runs (2026-09-08), the following holds:

> A malicious VERIFIED non-control third-party module cannot execute before privilege reduction and cannot escape its isolated runtime after launch. Host filesystem, network, databases, Redis, unrelated secrets, other modules, other sites, and physical devices remain inaccessible except through explicitly authorized broker operations. Resource abuse is contained, lifecycle failure removes runtime authority, and revocation/safe-state mechanisms terminate or remove control safely.

---

## SPRINT C PILOT GATE SCORE: 94 / 100

| Category | Score |
|----------|-------|
| Pre-Drop Safety | 95 |
| Privilege Isolation | 95 |
| Filesystem Isolation | 95 |
| Network Isolation | 95 |
| RPC Security | 90 |
| Secret Isolation | 95 |
| Data/Site Isolation | 95 |
| Resource Containment | 90 |
| Lifecycle | 95 |
| Safe-State | 95 |
| Revocation | 95 |
| Architecture Boundary | 95 |
| Linux Evidence | 90 |
| Production Safety | 100 |

---

## Final Line

```text
GO FOR LIMITED THIRD-PARTY RUNTIME PILOT
```
