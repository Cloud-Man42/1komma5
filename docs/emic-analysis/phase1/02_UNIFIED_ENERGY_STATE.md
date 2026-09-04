# UnifiedEnergyState

**Status:** Implemented  
**Package:** `packages/energy-core/src/energy_core/energy/`

---

## Purpose

Single canonical runtime model for site energy flows, replacing ad-hoc dicts and parallel state types across charging policy, widget/display snapshots, and optimization context.

---

## Model

**File:** [`unified.py`](../../../packages/energy-core/src/energy_core/energy/unified.py)

| Type | Role |
|------|------|
| `UnifiedEnergyState` | Root dataclass: `site_id`, `site_slug`, `timestamp`, freshness, sections |
| `DataFreshness` | `LIVE`, `FRESH`, `STALE`, `DEGRADED`, `OFFLINE`, `UNKNOWN` |
| `SolarSection` | Production kW, today kWh, forecast fields |
| `GridSection` | Import/export kW and today kWh |
| `BatterySection` | SoC, charge/discharge kW, capacity, state |
| `HouseSection` | Consumption kW and today kWh |
| `EvSection` | Connected, charging, power, SoC, departure |
| `SpaSection`, `HvacSection` | Optional load power and state |
| `PricesSection` | Import/export prices SEK/EUR, tier |
| `WeatherSection`, `ForecastSection` | Weather and forecast summaries |
| `HealthSection` | Per-provider `ProviderHealth` (heartbeat, charge_amps, mercedes, weather, spa) |

All section dataclasses are frozen with `slots=True`. Units are **kW/kWh** at the unified layer (W converted at adapter boundary).

---

## Adapters

**File:** [`unified_adapters.py`](../../../packages/energy-core/src/energy_core/energy/unified_adapters.py)

| Function | Source | Notes |
|----------|--------|-------|
| `from_energy_state()` | `EnergyState` (charging policy) | W → kW via `_w_to_kw`; maps EV/battery/grid/solar |
| `from_site_snapshot()` | `EnergySiteSnapshot` (widget/display) | Already kW-based; uses `EvState` for connected/charging |
| `from_snapshot_payload()` | `site_live_snapshots` JSON | Maps `live`, `today`, `solar`, `economy`, `ev`, `source_status` keys |

Helper: `_parse_freshness()` normalises string freshness to `DataFreshness` enum.

---

## Consumers

| Module | Usage |
|--------|-------|
| `energy_core/optimization/context.py` | `OptimizationContext.state: UnifiedEnergyState` |
| Future Phase 2 | Battery Opportunity Engine, Horizon Optimizer |

Phase 1 does **not** change API response shapes — adapters prepare for downstream optimizers without breaking existing routes.

---

## Tests

[`packages/energy-core/tests/energy/test_unified_state.py`](../../../packages/energy-core/tests/energy/test_unified_state.py) — adapter round-trips, unit conversion, freshness mapping, empty/missing fields.
