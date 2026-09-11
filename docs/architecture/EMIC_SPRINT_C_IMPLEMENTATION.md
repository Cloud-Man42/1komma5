# Sprint C Implementation (Step 5C.5)

## Delivered

1. **Config** — `THIRD_PARTY_RUNTIME_ENABLED`, `ISOLATED_RUNTIME_*` paths, sandbox mode, RPC/resource limits
2. **Migration 069** — `isolated_runtime_instances`, `runtime_events`, `runtime_control_leases`
3. **Sandbox** — `LinuxBubblewrapLauncher`, `SubprocessSandboxLauncher`, worker bootstrap
4. **RPC** — JSON-RPC 2.0, Unix socket (Linux) / TCP localhost (Windows dev)
5. **Brokers** — secret, network, device control, data read
6. **Orchestrator** — `IsolatedModuleAdapter`; loader skips in-process import for isolated tier
7. **R-3 fix** — `merge_advisory_bundles()` with explicit withdrawal/supersession
8. **Admin API + UI** — runtime diagnostics, blocked message, no Run button
9. **Fixtures** — `integration.sandbox-demo` (no `energy_core` imports in worker)
10. **Tests** — isolation suite + architecture guards

## Key files

```
packages/energy-core/src/energy_core/platform/modules/isolation/
packages/energy-core/src/energy_core/platform/modules/brokers/
packages/energy-core/src/emic_runtime_sdk/
scripts/isolated_runtime_bootstrap.py
scripts/sprint-c-prod-acceptance.ps1
backend/app/api/module_runtime.py
frontend/src/components/modules-devices/runtime/
```

## Deploy

Collector image includes `bubblewrap`, `emic-module` user, bootstrap script. Prod remains dormant until hard-security sign-off.
