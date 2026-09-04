# Phase 14 — Horizon Optimizer

## Goal

Read-only joint 48h planning for flexible loads (EV, spa) plus battery guidance, without activating control.

## Deliverables

- `energy_core.energy_optimizer.horizon` — `HorizonOptimizerSnapshot`, `build_horizon_optimizer_snapshot()`
- `SiteEnergyOrchestratorService.plan_horizon_readonly()` — live horizon + orchestrator, no DB writes
- `GET /api/sites/{slug}/horizon-optimizer` — monitor-only JSON plan + nested battery advice
- Frontend `HorizonOptimizerCard` on intelligence dashboard and diagnostics
- Unit + API + frontend tests

## Notes

- Reuses `EnergyHorizonBuilder`, `EnergyOrchestrator`, and Phase 13 battery advisor
- `monitor_only: true` always — no write/control side effects
