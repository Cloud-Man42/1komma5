# Phase 13 — Battery Opportunity Advisor

## Goal

Read-only battery guidance for operators, derived from existing EOV/strategy logic without activating control.

## Deliverables

- `energy_core.energy_optimizer.advisor` — `BatteryOpportunityAdvice`, `build_battery_opportunity_advice()`
- `GET /api/sites/{slug}/battery-opportunity` — monitor-only JSON advice
- Frontend `BatteryOpportunityCard` on intelligence dashboard
- Unit + API + frontend tests

## Notes

- Reuses `build_current_strategy_for_slug()`; no duplicate price/EOV math
- `monitor_only: true` always — no write/control side effects
