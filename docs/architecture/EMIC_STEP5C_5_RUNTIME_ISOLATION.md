# EMIC Step 5C.5 Runtime Isolation

## Scope

Third-party module execution in an out-of-process sandbox with JSON-RPC boundary, host-side brokers, and dormant production defaults.

## Components

| Component | Path |
|-----------|------|
| Runtime manager | `platform/modules/isolation/manager.py` |
| RPC gateway | `platform/modules/isolation/rpc/` |
| Brokers | `platform/modules/brokers/` |
| Worker bootstrap | `scripts/isolated_runtime_bootstrap.py` |
| Runtime SDK | `emic_runtime_sdk/` |
| DB migration | `069_isolated_module_runtime` |

## Production defaults (dormant)

- `THIRD_PARTY_RUNTIME_ENABLED=false`
- `CONTROL_ISOLATION_GATE_OPEN=false` (code constant; no env override)
- VERIFIED/ORG_APPROVED packages register metadata only; no in-process `importlib` for isolated tier

## State machine

`PREPARING → STARTING → HANDSHAKING → READY → RUNNING → STOPPING → STOPPED`

Failure paths: `CRASHED`, `QUARANTINED`, `BLOCKED`, `DEGRADED`

## Admin surface

- `GET /api/modules/runtime` — diagnostics list (admin token)
- Frontend **Runtime Isolation** panel — no Run/Enable control

## References

- [EMIC_MODULE_RUNTIME_ISOLATION.md](EMIC_MODULE_RUNTIME_ISOLATION.md)
- [EMIC_RUNTIME_SANDBOX_DECISION.md](EMIC_RUNTIME_SANDBOX_DECISION.md)
- [EMIC_SPRINT_C_IMPLEMENTATION.md](EMIC_SPRINT_C_IMPLEMENTATION.md)
