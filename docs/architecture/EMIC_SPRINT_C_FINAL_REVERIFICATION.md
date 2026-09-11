# EMIC Sprint C — Final Hard Security Re-Verification

**Date:** 2026-09-08  
**Verifier:** Independent re-verification (post Sprint C.6)  
**Production target:** `192.168.50.54`  
**Scope:** Step 5C.5 / Sprint C third-party runtime isolation — final pilot gate

---

## Executive Summary

Sprint C.6 claims were **partially confirmed** by independent re-run of production checks and the mandatory Linux isolation suite (**15 passed, 0 failed, 0 skipped**). Static analysis of the startup path shows **no attacker-controlled Python module import or entrypoint execution before privilege drop**; only trusted bootstrap code reads `manifest.json` (JSON parse) and performs RPC `Handshake`.

However, this re-verification **did not obtain the experimental pre-drop adversarial evidence** required by the final gate (sitecustomize/usercustomize, malicious `__init__`, canaries, forced setuid failure). Several broker, lifecycle, revocation, and safe-state controls remain **unit-tested only**, not proven from a live isolated Linux sandbox via RPC. The production **collector container** (`bwrap 0.8.0`) was not the environment used for the Linux adversarial matrix (host `bwrap 0.9.0`).

**Primary security question:** Can a malicious VERIFIED non-control module escape isolation?

**Answer with current evidence:** **NO** for post-drop filesystem/network/resource boundaries (Linux probes PASS). **UNKNOWN** for pre-drop root window and several broker/lifecycle/revocation paths (not experimentally proven end-to-end from sandbox).

---

## Final Verdict

```text
NO-GO FOR LIMITED THIRD-PARTY RUNTIME PILOT
```

---

## Previous Finding Closure (C.6 claims)

| Claim | Independent result |
|-------|-------------------|
| F-01 migration 069 | **CONFIRMED** — `069_isolated_module_runtime (head)` |
| F-02 Linux 15/0/0 | **CONFIRMED** — rerun 2026-09-08, same counts |
| F-03 prod acceptance | **CONFIRMED** — all checks PASS |
| F-09 resource proof | **CONFIRMED** — fork/fd/memory/rlimit integration PASS |
| Prod health | **CONFIRMED** |
| Prod runtime consistency | **CONFIRMED** |
| Flags dormant | **CONFIRMED** — empty/false |
| No runtime processes | **CONFIRMED** — no bootstrap/sandbox workers on host |

---

## Pre-Drop Root Window Analysis

### Actual startup path (verified in source)

```text
IsolatedModuleRuntimeManager.start_runtime()
  → LinuxBubblewrapLauncher.launch()          [host root when collector/tests use sudo]
  → bwrap (--unshare-net, --unshare-pid, …)   [no --cap-drop ALL when launcher euid==0]
  → python -I -s /bootstrap.py
  → main():
       1. Read env (launcher-controlled)
       2. json.loads(/package/manifest.json)   ← attacker JSON only, no import
       3. _rpc_call("Handshake", …)           ← trusted bootstrap + gateway validation
       4. _drop_module_identity()             ← setgid/setuid → 10001
       5. _apply_sandbox_hardening()          ← prctl NO_NEW_PRIVS + setrlimit
       6. _load_module_entry()                ← FIRST package Python execution
       7. runtime.start() / tick loop
```

### Pre-drop code rule assessment

| Check | Result | Evidence |
|-------|--------|----------|
| Only trusted bootstrap before drop | **PASS (code)** | `isolated_runtime_bootstrap.py` has no `energy_core` import; no `importlib` before step 6 |
| No package import before drop | **PASS (code)** | `_load_module_entry` after `_drop_module_identity` |
| PYTHONPATH isolation | **PASS (code)** | bwrap sets `PYTHONPATH=/sdk`; Python launched with `-I -s` |
| sitecustomize / usercustomize | **NOT TESTED** | No malicious fixture executed |
| Malicious `__init__.py` | **NOT TESTED** | Loader targets explicit module file; no adversarial fixture |
| Malicious entrypoint at root | **NOT TESTED** | Post-drop uid probes PASS in Linux suite |
| Pre-drop canary read/write | **NOT TESTED** | — |
| Drop failure fail-closed | **PARTIAL** | `setuid`/`setgid` raise on failure (no catch); **no test**, no audit event |
| Supplementary groups cleared | **NOT TESTED** | `setgid` then `setuid` only |
| Resource limits before module code | **PASS (code)** | `_apply_sandbox_hardening()` before `_load_module_entry()` |

### Handshake minimality (pre-drop)

Fields sent: `startup_token`, `module_id`, `version`, `artifact_sha256`, `runtime_instance_id`, `protocol_version`, `site_id`.

Gateway validates against pre-registered `ActiveRuntimeContext` record and consumes single-use startup token. No dynamic import, file write, or method dispatch from handshake params in bootstrap.

### Pre-drop concern (design, not exploit found)

When launcher runs as root, bwrap omits `--cap-drop ALL` so bootstrap can `setuid(10001)`. During handshake the worker is **root with full capabilities**, but only EMIC-owned bootstrap code runs. **No exploit identified**, but **no adversarial pre-drop tests** were executed to prove sitecustomize/canary/drop-failure behavior.

---

## Linux Adversarial Evidence (independent rerun)

**Command:** `scripts/run-linux-isolation-suite.sh` on `192.168.50.54` (after CRLF fix)  
**Date:** 2026-09-08

```text
collected: 15 (integration marker)
passed:    15
failed:    0
skipped:   0
```

### Environment note (F-RV-02)

| Component | Production collector | Test host (suite runner) |
|-----------|---------------------|--------------------------|
| bwrap version | **0.8.0** | **0.9.0** |
| `--no-new-privs` CLI | Not supported | Not supported |
| `--rlimit` CLI | Not supported | Not supported |
| Enforcement path | bootstrap `prctl` + `setrlimit` | Same code deployed |
| Runtime location | Inside collector container | Host venv + sudo root launcher |

Both versions use the **same bootstrap fallback path** (`bwrap_compat.py` probes false → env vars → bootstrap hardening). **Adversarial matrix was not executed inside the running collector container.**

---

## Sandbox Evidence (post-drop, Linux)

| Probe | Result |
|-------|--------|
| Host filesystem (`/etc/passwd`, `/home`, …) | **DENIED** |
| Environment scrub | **PASS** |
| Runtime not root (uid/euid 10001) | **PASS** |
| Direct network matrix | **DENIED** |
| Capabilities dropped | **PASS** |
| Docker socket | **DENIED** |
| Cross-module / foreign data | **DENIED** |
| Package read-only | **PASS** |
| Private `/tmp` | **PASS** |
| Privilege escalation (setuid/mount/ptrace/…) | **DENIED** |
| Fork / FD / memory / rlimit | **CONTAINED** |

---

## Broker Evidence

| Area | Result | Notes |
|------|--------|-------|
| Secret broker cross-module | **PASS** | Unit test |
| Secret broker cross-site | **PASS** | Unit test |
| Secret RPC permission | **PASS** | Gateway unit test |
| Network RPC permission | **PASS** | Gateway unit test |
| Redirect→private | **PASS** | **Mocked** httpx — not live sandbox RPC |
| DNS rebinding | **PASS** | **Mocked** DNS — not live sandbox RPC |
| Network broker positive E2E from sandbox | **NOT TESTED** | — |
| Secret broker E2E from sandbox | **NOT TESTED** | — |
| Read broker cross-site | **PASS** | Unit test |

---

## Resource Evidence

| Probe | Result |
|-------|--------|
| CPU rlimit configured | **PASS** (probe_rlimits) |
| Memory containment | **PASS** (probe_memory) |
| Fork containment | **PASS** |
| FD containment | **PASS** |
| Disk quota live abuse | **NOT TESTED** on Linux |

---

## Lifecycle Evidence

| Check | Result | Notes |
|-------|--------|-------|
| Heartbeat supervisor E2E | **NOT TESTED** Linux | Unit mock (`test_runtime_supervisor.py`) |
| Hung runtime termination | **NOT TESTED** Linux | — |
| Crash-loop quarantine | **PASS** unit | Mock manager |
| Old token after restart | **PASS** unit | `test_rpc_auth.py` |
| Bounded restart/backoff | **PARTIAL** | Unit only |

---

## Safe-State & Control Evidence

| Check | Result | Notes |
|-------|--------|-------|
| Explicit lease acquisition | **PASS** unit | `test_control_leases.py` |
| No auto re-grant on expiry | **PASS** unit | |
| Dead runtime command denied | **PARTIAL** | Unit only |
| Cross-site control | **PASS** unit | |
| Safe-state E2E | **NOT TESTED** Linux | |

---

## Revocation Evidence

| Check | Result | Notes |
|-------|--------|-------|
| RuntimeSecurityMonitor wired | **PASS** code | `manager.supervise_tick()` |
| Revocation stops runtime E2E | **NOT TESTED** | No test file |
| Critical advisory transition E2E | **NOT TESTED** | — |
| Advisory R-3 | **PASS** unit | `test_marketplace_revocation_policy.py` |

---

## Production Evidence (independent)

| Check | Result |
|-------|--------|
| Migration 069 | **PASS** |
| Collector bwrap | **PASS** — `/usr/bin/bwrap`, 0.8.0 |
| Bootstrap in image | **PASS** — `/app/scripts/isolated_runtime_bootstrap.py` |
| Runtime code in image | **PASS** — `linux_bwrap.py` at expected path |
| THIRD_PARTY_RUNTIME_ENABLED | **false** / unset |
| CONTROL_ISOLATION_GATE_OPEN | **false** / unset |
| Prod acceptance | **PASS** |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |
| Runtime API anonymous | **DENIED** |
| Runtime API admin | **ALLOW** |
| runtime_blocked flag | **true** |
| Third-party processes | **none** |

No physical device commands were issued during verification.

---

## Regression Evidence

| Suite | Result | Counts |
|-------|--------|--------|
| Full Python | **PASS** | 1672 passed, 24 skipped |
| Frontend | **PASS** | 734 passed |
| Architecture + isolation (Windows) | **PASS** | 89 passed, 17 skipped (Linux integration) |
| Architecture guards Step 5C | **PASS** | SDK/bootstrap/isolation boundary tests |
| Mandatory Linux integration | **PASS** | 15/0/0 on prod host |

Step 5B / Sprint A / Sprint B: covered by full pytest suite PASS (no separate counter in this run).

---

## Findings

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| F-RV-01 | **HIGH** | Pre-drop adversarial fixtures not executed (sitecustomize, `__init__`, canaries, drop-failure) | Open |
| F-RV-02 | **HIGH** | Linux matrix run on host bwrap 0.9.0, not inside production collector container bwrap 0.8.0 | Open |
| F-RV-03 | **HIGH** | Lifecycle/heartbeat/crash-loop not proven Linux sandbox E2E | Open |
| F-RV-04 | **HIGH** | Revocation/advisory runtime stop not proven E2E | Open |
| F-RV-05 | **HIGH** | Safe-state E2E not proven on Linux | Open |
| F-RV-06 | **HIGH** | Network/secret broker redirect/DNS/allow not proven from live sandbox RPC | Open |
| F-RV-07 | **MEDIUM** | `RuntimeSecurityMonitor` has no automated tests | Open |
| F-RV-08 | **MEDIUM** | Drop failure emits no explicit security audit event | Open |
| F-RV-09 | **INFO** | Root-capable handshake window by design; mitigated by bootstrap-only code | Accepted risk |

**BLOCKER count:** 0  
**Unresolved HIGH:** 6 (F-RV-01 – F-RV-06)  
**Security-boundary MEDIUM:** 2 (F-RV-07, F-RV-08) → treated as HIGH for this gate

---

## SPRINT C FINAL SECURITY SCORE

```text
SPRINT C FINAL SECURITY SCORE: 68 / 100
```

| Category | Score | Notes |
|----------|-------|-------|
| Pre-Drop Safety | 55 | Code path sound; adversarial tests missing |
| Privilege Isolation | 75 | Linux uid/gid probes PASS |
| Filesystem Isolation | 80 | Linux adversarial PASS |
| Network Isolation | 70 | Direct deny proven; broker E2E from sandbox not |
| RPC Security | 78 | Auth/replay/impersonation unit tests PASS |
| Secret Isolation | 65 | Broker unit tests; sandbox E2E missing |
| Data Isolation | 72 | Cross-site unit tests |
| Multi-Site Isolation | 72 | Unit tests PASS |
| Device-Control Boundary | 60 | Synthetic broker unit; no Linux E2E |
| Resource Containment | 78 | Linux abuse probes PASS |
| Lifecycle Safety | 50 | Unit mocks only |
| Safe-State | 55 | Unit partial |
| Revocation | 45 | Code wired; E2E missing |
| Architecture Boundaries | 88 | Guards PASS |
| Linux Evidence | 72 | 15/0/0 host; collector path gap |
| Production Safety | 85 | Migration, flags, acceptance PASS |

---

## SPRINT C FINAL HARD SECURITY RE-VERIFICATION

### PRE-DROP

| Check | Result |
|-------|--------|
| Only trusted bootstrap before drop | **PASS** (code review) |
| No attacker import before drop | **PASS** (code review) |
| sitecustomize/usercustomize blocked | **NOT TESTED** |
| Malicious `__init__` executes low privilege | **NOT TESTED** |
| Entrypoint executes low privilege | **PASS** (Linux probe_uid) |
| Drop failure fail-closed | **PARTIAL** (code only) |
| Supplementary groups removed | **NOT TESTED** |
| Privilege regain denied | **PASS** (Linux privesc probes) |
| NoNewPrivileges effective | **PASS** (bootstrap prctl + Linux caps probe) |
| Resource limits before module code | **PASS** (code order + probe_rlimits) |

### LINUX SANDBOX

| Check | Result |
|-------|--------|
| Production-equivalent path | **PARTIAL** (host not collector) |
| 0 mandatory skips | **PASS** |
| Host filesystem denied | **PASS** |
| Host secrets denied | **PASS** |
| Docker socket denied | **PASS** |
| Other module files denied | **PASS** |
| Package read-only | **PASS** |
| Direct network denied | **PASS** |
| DB denied | **PASS** (network matrix) |
| Redis denied | **PASS** (network matrix) |
| Privilege escalation denied | **PASS** |

### BROKERS

| Check | Result |
|-------|--------|
| Network broker | **PARTIAL** (unit/mock) |
| Redirect→private denied | **PASS** (mock) |
| DNS rebinding denied | **PASS** (mock) |
| Secret broker | **PARTIAL** (unit) |
| Cross-module secret denied | **PASS** (unit) |
| Cross-site secret denied | **PASS** (unit) |
| Read broker site isolation | **PASS** (unit) |

### RPC

| Check | Result |
|-------|--------|
| Authentication | **PASS** |
| Identity binding | **PASS** |
| Replay denied | **PASS** |
| Post-stop token denied | **PASS** |
| Impersonation denied | **PASS** |
| Limits/timeouts | **PASS** |

### RESOURCES

| Check | Result |
|-------|--------|
| CPU contained | **PASS** |
| Memory contained | **PASS** |
| Fork/process contained | **PASS** |
| FD contained | **PASS** |
| Disk bounded | **NOT TESTED** Linux |

### LIFECYCLE

| Check | Result |
|-------|--------|
| Heartbeat supervisor | **FAIL** (no Linux E2E) |
| Hung runtime termination | **FAIL** |
| Bounded restart | **PARTIAL** |
| Crash-loop quarantine | **PARTIAL** (unit) |
| Old token invalid after restart | **PASS** (unit) |

### CONTROL SAFETY

| Check | Result |
|-------|--------|
| Explicit lease | **PASS** (unit) |
| Explicit renewal | **PASS** (unit) |
| No automatic re-grant | **PASS** (unit) |
| Dead runtime command denied | **PARTIAL** |
| Cross-site control denied | **PASS** (unit) |
| Safe-state E2E | **FAIL** |

### SECURITY TRANSITIONS

| Check | Result |
|-------|--------|
| Publisher revocation | **FAIL** (no E2E) |
| Release/module revocation | **FAIL** |
| Key revocation | **N/A** |
| Lease removal | **PARTIAL** |
| Capability removal | **PARTIAL** |
| Session invalidation | **PASS** (unit) |
| Critical advisory transition | **FAIL** |
| Advisory R-3 | **PASS** (unit) |

### PRODUCTION

| Check | Result |
|-------|--------|
| Migration 069 | **PASS** |
| Correct prod image | **PASS** |
| bwrap compatibility reviewed | **PARTIAL** |
| THIRD_PARTY_RUNTIME_ENABLED=false | **PASS** |
| CONTROL_ISOLATION_GATE_OPEN=false | **PASS** |
| No general runtime start | **PASS** |
| No third-party runtime left running | **PASS** |
| Prod acceptance | **PASS** |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |
| Prod logs | **NOT REVIEWED** (this run) |
| No physical side effects | **PASS** |

### REGRESSION

| Check | Result |
|-------|--------|
| Full Python | **PASS** — 1672 passed, 24 skipped |
| Frontend | **PASS** — 734 passed |
| Architecture | **PASS** |
| Sprint C isolation (Windows) | **PASS** — 42 passed, 17 skipped |

---

## Required Actions Before Pilot GO

1. Execute pre-drop adversarial fixture suite on Linux (sitecustomize, malicious `__init__`, canaries, forced setuid failure).
2. Run mandatory Linux matrix **inside production collector container** (or prove equivalence).
3. Add Linux E2E tests for heartbeat/hang, crash-loop, revocation stop, safe-state (synthetic device only).
4. Prove network/secret broker allow/deny from live sandbox via `NetworkRequest` / `GetSecret` RPC.
5. Add tests for `RuntimeSecurityMonitor` and drop-failure audit events.

---

## Pilot Restrictions (if GO were issued later)

A future GO would authorize **only**:

- One explicitly approved module at a time
- VERIFIED or ORG_APPROVED only
- **NON-CONTROL** only
- No physical device commands
- Minimal permissions, strict network allowlist, no broad secret access
- Full runtime audit; automatic quarantine/revocation active
- `THIRD_PARTY_RUNTIME_ENABLED` enabled only per explicit admin action for one module

**Still blocked after any GO:**

- COMMUNITY runtime → DENY
- Control-capable third-party → DENY
- `CONTROL_ISOLATION_GATE_OPEN=true` → DENY without separate control gate
- Public unrestricted marketplace execution

---

## Final Security Statement (defensibility)

> A malicious VERIFIED non-control third-party module cannot execute attacker-controlled Python before privilege reduction in the **current bootstrap design** (code review). Once running at uid 10001, Linux probes show filesystem and direct network isolation **hold**. Privileged operations require brokers; resource abuse is contained in tested dimensions.

**However**, the statement cannot be fully defended with **experimental evidence** for the pre-drop window, collector-container path, broker RPC E2E from sandbox, or lifecycle/revocation/safe-state transitions. Therefore:

```text
NO-GO FOR LIMITED THIRD-PARTY RUNTIME PILOT
```
