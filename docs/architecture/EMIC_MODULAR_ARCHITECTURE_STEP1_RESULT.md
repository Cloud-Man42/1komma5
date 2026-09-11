# EMIC Modular Architecture — Step 1 Result

> **Superseded:** This document is a historical snapshot from 2026-09-05.  
> See [EMIC_STEP1_VERIFICATION.md](./EMIC_STEP1_VERIFICATION.md) (2026-09-07) for verified current state.

**Date:** 2026-09-05  
**Status:** Complete  
**Analysis reference:** [EMIC_MODULAR_ARCHITECTURE_STEP1.md](./EMIC_MODULAR_ARCHITECTURE_STEP1.md)

---

## Summary

Step 1 foundation for the modular monolith is implemented inside `energy_core` with re-export shims. No integration migrations, no database schema changes, and no API contract changes were made.

---

## Deliverables

### New packages

| Package | Purpose |
|---------|---------|
| `energy_core/contracts/` | Canonical ports: charging, energy, vehicles, pricing, forecasting, spa, health, capabilities, telemetry, meter helpers |
| `energy_core/platform/` | Device registry, module registry, lifecycle, health aggregator, event bus |
| `energy_core/mocks/` | Vendor-neutral `MockCharger`, `MockInverter`, `MockBattery`, `MockPriceProvider`, `MockSpa` |

### Consolidations

- **ChargerAdapter / ChargerCapabilities** — canonical framework types; `halo_adapter.py` and `capabilities.py` are shims
- **HealthStatus** — unified enum in `contracts/health.py` with mappers from four domain enums
- **STALE_TELEMETRY_SECONDS** — moved to `contracts/telemetry.py`; `vehicles/mercedes/constants.py` re-exports
- **MeterSnapshot helpers** — moved to `contracts/devices/meter.py`; `chargers/meter_adapter.py` re-exports
- **ChargingEventBus** — lifted to `platform/events/bus.py`; `vehicles/charging_intelligence/events.py` shim

### Registry dispatch

- `chargers/framework/factory.py` — `_INTEGRATION_BUILDERS` map (Charge Amps registered)
- `energy_control/provider_factory.py` — `_CONTROL_PROVIDER_REGISTRY` map (noop, heartbeat, chargeamps)

### Removed dead code

- Deleted `energy_core/devices/` (empty placeholder, zero imports verified)

---

## Test results

| Suite | Before Step 1 | After Step 1 |
|-------|---------------|--------------|
| Python (pytest) | 1215 | **1256** (+41 new tests) |
| Frontend (Vitest) | 691 | **692** |
| Full `.\test-windows.ps1` | green | **green** (exit 0) |

### New test modules

- `packages/energy-core/tests/architecture/test_layering.py` — layer rules + baseline allowlist
- `packages/energy-core/tests/contracts/` — capabilities, health mappings, meter, telemetry
- `packages/energy-core/tests/platform/` — event bus, module registry, device registry
- `packages/energy-core/tests/mocks/test_mock_providers.py`
- `backend/tests/test_modular_characterization.py` — dashboard/vehicle stale behavior

---

## Architecture test baseline (documented debt)

The allowlist captures pre-existing vendor coupling. **New entries fail CI**; the list must shrink over time.

### Mercedes imports outside `vehicles/mercedes/` (13 files)

- `backend/app/api/dashboard.py`, `backend/app/api/vehicles.py`
- `db/attribute_observation_repo.py`, `db/vehicle_repo.py`
- `vehicles/commands/service.py`, `connection_signals.py`, `diagnostics/self_heal.py`
- `vehicles/health.py`, `polling.py`, `sessions/session_service.py`
- `vehicles/supervisor.py`, `sync_service.py`, `value_envelope.py`

### Charge Amps imports outside `chargers/` (10 files)

- `backend/app/api/ev_chargers.py`, `backend/app/api/system.py`, `backend/app/main.py`
- `collector/app/collector.py`
- `charging/readiness.py`, `energy_balance/coordinator.py`
- `energy_control/chargeamps_provider.py`, `energy_control/provider_factory.py`
- `ev_accounting/coordinator.py`, `ev_accounting/session_service.py`

---

## Performance baseline

Attempted `scripts/performance-baseline.ps1` against `http://localhost:8000` — backend not available locally (0/N requests succeeded). Production baseline comparison deferred; no code paths in Step 1 affect hot request handlers beyond shim imports.

---

## Not changed (as planned)

- `backend/app/schemas.py`, `db/models.py`, Alembic migrations
- Vendor client implementations (Mercedes, Charge Amps, Arctic Spa, Heartbeat)
- `display_service.py` ↔ `dashboard.py` layer inversion (Step 2)
- `ev_accounting/` ChargeAmpsMeterAdapter construction (Step 2)
- Solar forecast / solar intelligence unification (Step 2–3)

---

## Step 2 preview

1. Charge Amps as reference integration (`integrations/chargeamps/`)
2. VehicleProvider factory/registry (replace hardcoded Mercedes in supervisor)
3. Dashboard compute extraction + fix display_service inversion
4. `ev_accounting` → `IMeterReader` port
5. Begin shrinking architecture allowlist
