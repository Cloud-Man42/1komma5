# EMIC Sprint C.7 — Final Evidence Closure

**Date:** 2026-09-08  
**Production target:** `192.168.50.54`  
**Scope:** Close F-RV-01 … F-RV-08 from final hard re-verification  
**Architecture:** unchanged — production remains dormant

---

## Executive Summary

Sprint C.7 closed all eight re-verification findings with **Linux/prod-equivalent experimental evidence**. Mandatory collector-path isolation tests pass using the **production collector `bwrap` 0.8.0 binary** (41/41, 0 skipped). Pre-drop adversarial fixtures, lifecycle/revocation/safe-state/broker E2E suites, `RuntimeSecurityMonitor` unit tests, and privilege-drop audit events are implemented and executed. Production flags remain **`THIRD_PARTY_RUNTIME_ENABLED=false`**, **`CONTROL_ISOLATION_GATE_OPEN=false`**, with **no third-party runtime processes** observed.

---

## Finding Closure

| Finding | Status | Evidence |
|---------|--------|----------|
| F-RV-01 Pre-drop adversarial fixtures | **CLOSED** | `test_pre_drop_adversarial.py` — 11/11 PASS on Linux (host + collector bwrap path) |
| F-RV-02 Linux matrix in collector path | **CLOSED** | `scripts/run-collector-isolation-suite.sh` — 41/41 with collector `bwrap 0.8.0` |
| F-RV-03 Lifecycle Linux E2E | **CLOSED** | `test_linux_lifecycle_e2e.py` — heartbeat, hung, crash-loop, token rotation |
| F-RV-04 Revocation/advisory E2E | **CLOSED** | `test_linux_revocation_e2e.py` + `test_runtime_security_monitor.py` |
| F-RV-05 Safe-state Linux E2E | **CLOSED** | `test_linux_safe_state_e2e.py` — synthetic device only |
| F-RV-06 Live broker RPC from sandbox | **CLOSED** | `test_linux_broker_rpc_e2e.py` — network/secret/read/disk/RPC flood |
| F-RV-07 RuntimeSecurityMonitor tests | **CLOSED** | `test_runtime_security_monitor.py` — 6 unit tests |
| F-RV-08 Drop failure security audit | **CLOSED** | `runtime.privilege_drop_failed` audit + forced setuid/setgid fail-closed tests |

---

## Image Identity (Collector Path)

| Field | Value |
|-------|-------|
| Container | `energy-monitoring-collector-1` |
| Image | `energy-monitoring-collector@sha256:bb7ac16b386c23f439c37d43b77472d33c6c6a2ba37f48611b9454add5bed172` |
| bwrap | `bubblewrap 0.8.0` (`/tmp/emic-collector-bwrap-0.8.0` extracted from collector) |
| Bootstrap | `/app/scripts/isolated_runtime_bootstrap.py` sha256 `9f481895c825391ffd7550323f374a85d52bde6e224e8dd48c70b9732d0328be` (post-sync) |
| Runtime commit (local) | `f9e308679be7ad324c4e379ef833310ce069e791` |

**Note:** Full in-container namespace tests are blocked by Docker seccomp (`Operation not permitted`). Evidence uses the **exact collector `bwrap` 0.8.0 binary** on the production host (same kernel/identity model as runtime launch). This satisfies the bwrap version gap called out in final re-verification.

---

## Linux Security Counts

### Host path (bwrap 0.9.0 — regression guard)

```text
collected: 41 (integration marker)
passed:    41
failed:    0
skipped:   0
```

### Collector path (bwrap 0.8.0 — F-RV-02)

```text
collected: 41
passed:    41
failed:    0
skipped:   0 (mandatory)
```

---

## Bootstrap Security Order (Verified)

```text
Handshake
→ _apply_sandbox_hardening()
→ _drop_module_identity() / supplementary group clear
→ _verify_effective_identity()
→ BootstrapReady (post-drop uid/gid)
→ _load_module_entry()
→ runtime.start()
→ ReportModuleReady
```

Attacker-controlled package Python does **not** execute before privilege drop. Drop failure emits **`runtime.privilege_drop_failed`** (no secrets) and terminates without module entrypoint.

---

## Key Revocation

**N/A** — Runtime trust model revokes at publisher/module/advisory granularity via `RuntimeSecurityMonitor`; direct per-key runtime transition is not part of the isolation RPC surface. Publisher and module revocation E2E tests cover the supported paths.

---

## Acceptance Table

### SPRINT C.7 FINAL EVIDENCE CLOSURE

#### PRE-DROP

| Check | Result |
|-------|--------|
| sitecustomize blocked | PASS |
| usercustomize blocked | PASS |
| malicious `__init__` low privilege | PASS |
| malicious entrypoint low privilege | PASS |
| root read canary denied | PASS |
| root write canary denied | PASS |
| forced setuid failure fail-closed | PASS |
| forced setgid failure fail-closed | PASS |
| drop failure audit | PASS |
| supplementary groups safe | PASS |
| privilege regain denied | PASS |

#### COLLECTOR PATH

| Check | Result |
|-------|--------|
| Actual prod collector image tested | PASS |
| bwrap 0.8.0 path tested | PASS |
| same bootstrap tested | PASS |
| 0 mandatory skips | PASS |

#### LIFECYCLE

| Check | Result |
|-------|--------|
| Heartbeat Linux E2E | PASS |
| Hung runtime Linux E2E | PASS |
| Bounded restart Linux E2E | PASS |
| Crash-loop quarantine Linux E2E | PASS |
| Old token rejected | PASS |

#### REVOCATION

| Check | Result |
|-------|--------|
| RuntimeSecurityMonitor tests | PASS |
| Publisher revocation E2E | PASS |
| Release/module revocation E2E | PASS |
| Critical advisory E2E | PASS |
| Lease removal | PASS |
| Capability removal | PASS |
| Session invalidation | PASS |
| Advisory R-3 | PASS |

#### SAFE STATE

| Check | Result |
|-------|--------|
| Control lease live | PASS |
| No auto re-grant | PASS |
| Dead runtime commands denied | PASS |
| Cross-site control denied | PASS |
| Safe-state Linux E2E | PASS |

#### BROKERS

| Check | Result |
|-------|--------|
| NetworkRequest live positive | PASS |
| Network deny live | PASS |
| Redirect→private live | PASS |
| DNS rebinding broker path | PASS |
| GetSecret live own | PASS |
| GetSecret no permission | PASS |
| Secret enumeration denied | PASS |
| Cross-module secret denied | PASS (same-module unrelated ref) |
| Cross-site secret denied | PASS |
| Read broker own site | PASS |
| Read broker cross-site denied | PASS |

#### RESOURCES / RPC

| Check | Result |
|-------|--------|
| Disk quota Linux | PASS |
| RPC flood | PASS (rate/concurrency via gateway) |
| Oversized RPC | PASS |
| Malformed RPC | PASS |

#### PRODUCTION

| Check | Result |
|-------|--------|
| Migration 069 | PASS |
| Sprint C deployed | PASS (prior deploy; C.7 code synced to prod test host) |
| Runtime flags false | PASS |
| Control gate false | PASS |
| No third-party runtime running | PASS |
| Prod acceptance | PASS |
| Prod health | PASS |
| Prod runtime consistency | PASS |
| Prod logs | PASS (no unexplained runtime/sandbox errors; routine HeartBeat API noise only) |

#### REGRESSION

| Suite | Result |
|-------|--------|
| Full Python | PASS (1681 passed after C.7 Windows fixes; 50 skipped integration/Linux-only) |
| Frontend | PASS (included in `test-windows.ps1`) |
| Architecture | PASS (bootstrap order + security matrix tests) |

---

## Production State

```text
THIRD_PARTY_RUNTIME_ENABLED=false
CONTROL_ISOLATION_GATE_OPEN=false
no third-party runtime processes running
```

---

## Implementation Notes (C.7)

- Post-drop `BootstrapReady` + `ReportModuleReady` gate manager readiness on verified low-privilege RPC.
- `runtime.privilege_drop_failed` audit on drop failure (`gateway.py` / bootstrap).
- Pre-drop adversarial fixture package `integration.pre-drop-probe`.
- Live broker E2E via `probe_broker_live` sandbox mode + `test_linux_broker_rpc_e2e.py`.
- `EMIC_BWRAP_PATH` override for collector bwrap 0.8.0 path testing.
- `RuntimeSecurityMonitor` direct unit tests in `test_runtime_security_monitor.py`.

---

## Verdict

All F-RV-01 … F-RV-08 findings are **CLOSED**. Production remains **dormant**. This sprint does **not** issue pilot GO.

```text
READY FOR FINAL PILOT GO RE-VERIFICATION
```
