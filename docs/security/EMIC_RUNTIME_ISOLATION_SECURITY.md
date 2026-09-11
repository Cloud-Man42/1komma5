# EMIC Runtime Isolation Security

## Trust boundary

Host collector owns: spawn, attestation, RPC auth, brokers, audit, lifecycle. Worker sees only `emic_runtime_sdk`, read-only package mount, and brokered RPC methods.

## RPC auth

1. Ephemeral startup token at spawn (single use, 60s TTL)
2. `Handshake` → HMAC-bound session token
3. Every non-handshake RPC validates runtime identity, module_id, site_id, session

Forbidden methods: generic `execute`, `eval`, `run_code`, `shell`.

## Limits

- Request/response size caps (`ISOLATED_RUNTIME_RPC_MAX_BYTES`)
- Per-method deadlines and rate limits
- Max concurrent in-flight RPC per runtime

## Adversarial matrix

| Case | Mitigation |
|------|------------|
| Filesystem escape | bwrap ro-bind + deny host paths (Linux integration) |
| Direct network | `--unshare-net`; broker allowlist |
| Secret cross-module | `SecretBroker` module+site scope |
| Cross-site read/control | Brokers enforce site_id match |
| RPC impersonation/replay | Session store + startup token consume |
| Digest substitution | Handshake artifact_sha256 binding |
| Crash / lease expiry | `DeviceControlBroker.revoke_runtime` → safe default power |

Tests: `packages/energy-core/tests/platform/isolation/`

## Logging

Worker stdout/stderr treated as untrusted; size-capped capture on host.
