# Phase 16 — Energy Control Activation

## Goal

Safe staged activation of the energy control loop with explicit provider and collector flags.

## Deliverables

- `ENERGY_CONTROL_PROVIDER` (default `noop`) — only noop supported in Phase 16
- `ENERGY_CONTROL_COLLECTOR_ENABLED` (default `true`) — global kill switch for slow-lane sync
- `resolve_control_provider()` — factory from settings
- Service + collector tests for RECOMMEND preview and AUTOMATIC apply paths

## Rollout

1. Set site `optimization_mode=RECOMMEND` → collector logs preview actions (noop)
2. Set `SEMI_AUTOMATIC` + `energy_control_enabled=true` → manual apply via API (noop)
3. Set `AUTOMATIC` only after validation — still noop until real provider added
