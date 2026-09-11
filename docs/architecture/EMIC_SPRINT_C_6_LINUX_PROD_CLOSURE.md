# EMIC Sprint C.6 — Linux Proof & Production Closure

**Date:** 2026-09-08  
**Scope:** Close operational blockers F-01, F-02, F-03, F-09 from Sprint C.5  
**Production target:** `192.168.50.54`

---

## Verdict

**READY FOR SPRINT C HARD SECURITY RE-VERIFICATION**

This does **not** authorize third-party runtime pilot GO. Independent re-verification is the next gate.

---

## Finding closure

| ID | Status | Evidence |
|----|--------|----------|
| F-01 | **CLOSED** | Prod `alembic current` → `069_isolated_module_runtime (head)` |
| F-02 | **CLOSED** | Linux isolation suite on prod-equivalent host: **15 passed, 0 failed, 0 skipped** (integration) |
| F-03 | **CLOSED** | `scripts/sprint-c-prod-acceptance.ps1` PASS (migration, bwrap, bootstrap, flags, runtime API auth) |
| F-09 | **CLOSED** | Live Linux probes: fork/fd/memory/rlimit containment + resource limits in adversarial extended tests |

### Regression carry-forward

| ID | Status |
|----|--------|
| F-04 | **PASS** |
| F-05 | **PASS** |
| F-06 | **PASS** |
| F-07 | **PASS** |
| F-08 | **PASS** |
| F-10 | **PASS** (code + Linux suite context) |
| F-11 | **PASS** (code + Linux suite context) |
| F-12 | **PASS** |
| F-13 | **PASS** |

---

## Code changes (minimal, verification-driven)

| Area | Change |
|------|--------|
| `bwrap_compat.py` | Probe distro bwrap for `--no-new-privs` / `--rlimit`; fallback via bootstrap `prctl` + `resource.setrlimit` |
| `linux_bwrap.py` | Ubuntu bwrap compatibility; socket dir bind-mount; `/tmp` 1777; post-handshake uid drop via bootstrap; omit `--cap-drop ALL` when launching as root |
| `isolated_runtime_bootstrap.py` | Handshake before privilege drop; `_drop_module_identity()` after handshake |
| `gateway.py` | Socket path traverse fix for dropped uid; parent dir chmod/chown when root |
| `manager.py` | Session-before-poll startup wait; stderr capture on startup failure |
| `sandbox_demo.py` | Probe fixes (evil_network summary, ptrace attach, mount tmpfs probe) |
| `test_linux_adversarial_extended.py` | Memory + rlimit Linux integration tests |
| `sprint-c-prod-acceptance.ps1` | Sudo-first remote docker when password available |

---

## Production deployment

| Check | Result |
|-------|--------|
| Migration 069 | **PASS** |
| Sprint C deployed | **PASS** (full deploy via `deploy-linux.ps1`) |
| bwrap present | **PASS** — `/usr/bin/bwrap`, bubblewrap 0.8.0 |
| bootstrap present | **PASS** — `/app/scripts/isolated_runtime_bootstrap.py` |
| low-privilege UID/GID | **PASS** — probe uid/gid 10001 in Linux suite |
| THIRD_PARTY_RUNTIME_ENABLED=false | **PASS** |
| CONTROL_ISOLATION_GATE_OPEN=false | **PASS** |
| Runtime API auth | **PASS** |
| No general runtime start | **PASS** (`runtime_blocked=true`) |
| Prod health | **PASS** (`verify-prod-health.ps1`) |
| Prod runtime consistency | **PASS** (`verify-prod-runtime-consistency.ps1 -Strict`) |

---

## Linux sandbox (prod-equivalent host `192.168.50.54`)

Executed via `scripts/run-linux-isolation-suite.sh` (root + host bwrap 0.9.0, prod-matching bootstrap/UID policy):

```
15 passed, 0 failed, 0 skipped (integration marker)
```

Includes: adversarial matrix, extended probes, fork/fd/memory/rlimit, sandbox launcher, fail-closed regression.

| Category | Result |
|----------|--------|
| Fail-closed | **PASS** |
| No root (module) | **PASS** |
| Host filesystem denied | **PASS** |
| Host secrets denied | **PASS** |
| Direct network denied | **PASS** |
| Package read-only | **PASS** |
| Cross-module / private temp | **PASS** |
| Fork/fd/memory/rlimit | **PASS** |
| Capabilities dropped | **PASS** |
| Privilege escalation denied | **PASS** |

---

## Regression (Windows dev host)

| Suite | Result |
|-------|--------|
| Full Python | **PASS** (`test-windows.ps1`) |
| Frontend | **PASS** — 734 tests |
| Isolation (Windows) | 42 passed, 17 skipped (Linux-only integration) |

---

## Final production safety state

| Flag | Value |
|------|-------|
| THIRD_PARTY_RUNTIME_ENABLED | `false` |
| CONTROL_ISOLATION_GATE_OPEN | `false` |
| Third-party runtime processes | **none running** |

---

## Acceptance table summary

See Sprint C.6 brief §75. All **PROD DEPLOYMENT**, **LINUX SANDBOX** (mandatory integration), **PROD ACCEPTANCE**, and **REGRESSION** rows required for C.6 closure are **PASS** except items explicitly delegated to independent hard re-verification (full broker E2E matrix, live prod abuse, controlled sandbox-demo prod probe without enablement).

---

## Notes for re-verification

1. Ubuntu host bwrap lacks `--no-new-privs` and `--rlimit`; enforcement is via bootstrap after RPC handshake.
2. Root-launched sandboxes use handshake-as-root → setuid(10001) → module probes; not user-namespace `--uid` (breaks unix socket access across ns).
3. Independent re-verification should re-run full mandatory Linux matrix and confirm no skip/xfail regression.
