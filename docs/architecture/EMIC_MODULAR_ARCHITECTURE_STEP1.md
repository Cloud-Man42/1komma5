# EMIC Modular Architecture — Step 1 Analysis

**Date:** 2026-09-05  
**Scope:** Architecture analysis and foundation for modular monolith migration  
**Status:** Analysis complete; foundation implementation in progress

---

## 1. Current Architecture

EMIC (Energy Monitoring In a Cloud) is a **uv workspace monorepo** deployed as a single Docker stack:

```text
Caddy (:443) → FastAPI backend (:8000) + Next.js frontend (:3000)
                    ↑
              Collector (asyncio poller, separate process)
                    ↓
         PostgreSQL/TimescaleDB + Redis
```

### Workspace members

| Package | LOC (approx) | Role |
|---------|-------------|------|
| `packages/energy-core` | ~55,400 | Domain logic, integrations, DB repos |
| `backend` | ~19,300 | FastAPI routes, schemas, display/widget services |
| `collector` | ~960 | Background polling (fast/medium/slow lanes) |
| `frontend` | ~49,700 | Next.js 15 dashboard UI |

### energy_core subpackages (37)

Flat namespace under `energy_core/` with no enforced layering. Largest: `vehicles/` (10.6k), `db/` (9k), `solar_forecast/` (3.5k), `solar_intelligence/` (2.2k), `spa_energy/` (2k), `charging/` (3.7k), `chargers/` (3.1k).

### Backend API layer

28 route modules, ~160 HTTP endpoints. Fat controllers: `vehicles.py` (1048 LOC), `spa.py` (1026), `ev_chargers.py` (854), `dashboard.py` (595), `solar_forecast.py` (548).

Dependency injection is minimal: `backend/app/deps.py` (46 lines) yields DB sessions; repos/services constructed inline in route handlers.

### Data layer

- **76 ORM models** in single `db/models.py` (1,587 lines)
- **33 repository modules** (~8,835 lines), hybrid domain-split + legacy monolith in `repositories.py`
- **61 Alembic migrations**, head revision `061_admin_audit_log`
- SQLite for dev, PostgreSQL/TimescaleDB for production

### Configuration

Flat `Settings` class with ~81 fields in `config.py`. No nested per-integration config objects. ChargeAmps credentials read from env vars in `chargeamps_config.py` (not in Settings).

### Scheduling

Ad-hoc `asyncio.create_task` + `while self._running` loops. No central scheduler abstraction. Collector runs fast (Heartbeat, ~30s), medium (300s), slow (900s) lanes. Vehicle supervisor runs Mercedes polling outside lane structure.

### Existing abstractions (preserve, do not rewrite)

| Contract | Location | Live implementations |
|----------|----------|---------------------|
| `ChargerAdapter` | `chargers/framework/models.py:284` | ChargeAmps only |
| `ChargerController` | `chargers/base.py:17` | ChargeAmps, Mock |
| `VehicleProvider` | `vehicles/abstractions/provider.py` | Mercedes, Mock |
| `IEnergyControlProvider` | `energy_control/provider.py` | noop, Heartbeat, ChargeAmps |
| `IMarketPriceProvider` | `price_engine/providers/base.py` | Heartbeat only |
| `WeatherForecastProvider` | `solar_forecast/weather.py` | Open-Meteo, DMI, Routing |
| `ISolarRadiationProvider` | `solar_intelligence/providers/` | SMHI STRÅNG, DMI |
| `HeartbeatProvider` | `providers/base.py` | OneKommaFive, Mock |
| `ChargingEventBus` | `vehicles/charging_intelligence/events.py` | In-process only |

---

## 2. Identified Architectural Problems

### P1: Vendor coupling in generic code

| Symbol | Current home | Imported by (non-vendor) |
|--------|-------------|--------------------------|
| `STALE_TELEMETRY_SECONDS` | `vehicles/mercedes/constants.py:44` | 11 files including `vehicles/polling.py`, `vehicles/health.py`, `backend/app/api/dashboard.py` |
| `MeterSnapshot`, `integrate_power_kwh` | `chargers/meter_adapter.py` | `ev_accounting/`, `virtual_evse/` |
| `build_chargeamps_connection_info` | `chargers/chargeamps_config.py` | `charging/readiness.py` |
| `ChargeAmpsMeterAdapter` construction | `ev_accounting/coordinator.py` | Direct vendor instantiation in domain |
| `MercedesProvider` hardcoded | `vehicles/supervisor.py:218` | No factory/registry |

### P2: Duplicate contracts

- Two `ChargerAdapter` Protocols: `framework/models.py:284` vs `halo_adapter.py:14`
- Two `ChargerCapabilities` dataclasses: `capabilities.py:9` vs `framework/models.py:108`
- Four health status enums with different values across domains

### P3: Factory dispatch via if/elif strings

- `chargers/framework/factory.py:36-44` — ChargeAmps + OCPP prefix check
- `energy_control/provider_factory.py:17-30` — noop/heartbeat/chargeamps
- `vehicles/supervisor.py:211-218` — test→Mock, prod→Mercedes only

### P4: Layer inversion

- `backend/app/display_service.py:11` imports from `app.api.dashboard`
- Business logic in route handlers (vehicles 1048 LOC, spa 1026 LOC)
- `schemas.py` monolith (1935 LOC) with vendor field names in API contract

### P5: Parallel forecast stacks

`solar_forecast/` (v2, 15-min) and `solar_intelligence/` (hourly Ridge) with duplicated physical models, calibration, and confidence scoring. Bridged via `intelligence_bridge.py` when `solar_intelligence_enabled=True`.

### P6: Duplicated calculations

- Actual solar kWh today: 7 resolution paths (`rollup_queries`, `daily_evaluation`, `historical`, `energy_state`, `aggregation`, `snapshots`, `integration.py`)
- Savings: 6+ paths (`financial/`, `charging/savings`, `heartbeat_audit`, `energy_state`, `snapshots`, `forecasting.py`)
- Local day bounds: triplicated in `daily_evaluation`, `price_engine/periods`

### P7: No architecture enforcement

Ruff only (line-length 100). No import-linter, no layer tests, no dependency rules.

### P8: Dead code

`energy_core/devices/` — 3 empty `__init__.py`, zero imports in entire repo.

---

## 3. Core Candidates

These belong in `platform/` (shared infrastructure, no vendor knowledge):

| Component | Current location | Notes |
|-----------|-----------------|-------|
| Site/property model | `db/repositories.py` SiteRepository | Keep repos, extract read models |
| Device registry | NEW `platform/devices/registry.py` | Projection over existing tables |
| Module registry | NEW `platform/modules/registry.py` | Static registration |
| Event bus | `vehicles/charging_intelligence/events.py` | Lift to platform |
| Health aggregation | `integrations/health.py` | Wrap, don't replace |
| Configuration | `config.py` | Keep flat for now |
| Secrets | `secrets.py` | Fernet via EMIC_SECRET_KEY |
| Logging/telemetry | `performance/` | Request ID, SQL tracking |
| Lifecycle | NEW `platform/lifecycle.py` | Thin wrapper |
| Energy integration | `energy/integration.py` | Core kWh math |
| Domain readings | `domain.py` | RawEnergyReading, NormalizedEnergyReading |
| Unified state | `energy/unified.py` | UnifiedEnergyState sections |

---

## 4. Feature Module Candidates

| Module | Current packages | LOC |
|--------|-----------------|-----|
| SmartCharging | `charging/`, `flexible_load/` | ~5k |
| SolarForecast | `solar_forecast/`, `solar_intelligence/` | ~5.7k |
| Economics | `financial/`, `export_revenue/`, `price_engine/` | ~2.5k |
| BatteryOptimization | `energy_optimizer/`, `energy_control/` | ~1.6k |
| SpaOptimization | `spa_energy/`, `consumer_accounting/` | ~2.7k |
| VehicleEnergy | `vehicles/`, `ev_accounting/` | ~12k |
| PeakShaving | `price_engine/peak_protection.py` | part of price_engine |
| Automation | `flexible_load/orchestrator.py`, `site_energy/` | ~1.3k |
| ForecastLearning | `forecast_learning/` | ~460 |
| EnergyBalance | `energy_balance/` | ~420 |

Feature modules must consume contracts, never vendor clients.

---

## 5. Integration Module Candidates

| Integration | Current location | Status | Adapter exists? |
|-------------|-----------------|--------|-----------------|
| Heartbeat (1KOMMA5) | `heartbeat/`, `providers/` | Live, primary data source | Partial |
| Charge Amps | `chargers/charge_amps*.py`, `framework/adapters/` | Live, only charger impl | Yes (framework) |
| Mercedes | `vehicles/mercedes/` (37 files) | Live, only vehicle impl | Provider only |
| Arctic Spa | `integrations/arctic_spa/`, `spa_energy/` | Live | Service, no port |
| Sungrow | `sungrow/` | Via Heartbeat proxy | Types only |
| Open-Meteo | `solar_forecast/open_meteo.py` | Live | ABC |
| SMHI STRÅNG/SNOW | `solar_intelligence/providers/` | Live (SE) | Protocol |
| DMI Harmonie | `solar_intelligence/providers/` | Live (DK) | Protocol |
| Nord Pool | via Heartbeat market API | Live | Heartbeat adapter |
| ChargeFinder | `integrations/charging_stations/chargefinder/` | Live | Full adapter |
| Sensibo | — | Not present | — |
| Ebeco | — | Not present | — |
| Gecko | — | Not present | — |

---

## 6. Shared Infrastructure

| Concern | Location | Notes |
|---------|----------|-------|
| Persistence | `db/` (33 files, 76 models) | Single models.py — split deferred |
| Caching | `cache/` L1 in-memory + L2 Redis | TieredCacheService, pub/sub for SSE |
| HTTP clients | Scattered in vendor modules | No shared HTTP abstraction |
| Messaging | `cache/snapshot_pubsub.py` | Redis pub/sub only |
| Logging | `performance/logging_context.py` | request_id via ContextVar |
| Credential encryption | `secrets.py` | Fernet, EMIC_SECRET_KEY |
| Migrations | `alembic/` (61 revisions) | Batch mode for SQLite |
| Testing | pytest (1215 backend + 691 frontend) | No architecture tests yet |

---

## 7. Direct Vendor Couplings

### API layer → vendor imports

| File | Vendor imports |
|------|---------------|
| `backend/app/api/vehicles.py` | `MercedesProvider`, `MercedesLoginFlow`, `MercedesAuthError` |
| `backend/app/api/heartbeat_bridge.py` | `HeartbeatEvBridgeService`, `HeartbeatWriteTestService` |
| `backend/app/api/ev_chargers.py` | `ChargerAdapterFactory`, `CHARGE_AMPS_CLOUD`, `create_heartbeat_client` |
| `backend/app/api/spa.py` | `ArcticSpaService`, `ArcticSpaConfiguration` |
| `backend/app/api/system.py` | `build_chargeamps_connection_info`, `build_heartbeat_connection_info` |
| `backend/app/api/dashboard.py` | `STALE_TELEMETRY_SECONDS` (inline Mercedes import) |
| `backend/app/main.py` | `assert_chargeamps_production_safe` |

### Domain → vendor imports (within energy_core)

| Generic module | Vendor import |
|---------------|--------------|
| `charging/readiness.py:8` | `chargeamps_config.build_chargeamps_connection_info` |
| `ev_accounting/coordinator.py:11` | `ChargeAmpsMeterAdapter` |
| `ev_accounting/session_service.py:10` | `ChargeAmpsMeterAdapter` |
| `energy_balance/coordinator.py:124` | `ChargeAmpsMeterAdapter.build(...)` |
| `vehicles/supervisor.py:30-31` | `MercedesProvider`, `MercedesTokenBundle` |
| `vehicles/commands/service.py:19-25` | Mercedes command builder |
| 6 generic vehicle files | `STALE_TELEMETRY_SECONDS` from mercedes.constants |

### API schema vendor field names

`sungrow_*_w`, `heartbeat_*`, `chargeamps_*`, `Mercedes EQE 500` defaults in `schemas.py`.

---

## 8. High-Risk Dependencies

| Risk | Impact | Mitigation |
|------|--------|------------|
| `db/models.py` monolith (76 models) | Any schema change affects all domains | No split in Step 1; document ownership |
| `schemas.py` monolith (1935 LOC) | API contract changes break frontend | Compatibility layer; no changes in Step 1 |
| Heartbeat as sole data source | Heartbeat down = no readings, prices, balance | Health isolation; stale data handling exists |
| Mercedes hardcoded in supervisor | Cannot add Tesla/BMW without rewrite | VehicleProvider factory in Step 2 |
| Dual solar forecast stacks | Confusion, duplicated calibration | Unified module boundary in Step 2-3 |
| `display_service` ↔ `dashboard` circular import | Refactoring dashboard breaks display | Extract shared compute layer in Step 2 |
| Collector + backend share DB | Schema migration must be backward-compatible | Alembic only; no destructive migrations |

---

## 9. Circular Dependencies

| Cycle | Files | Severity |
|-------|-------|----------|
| display_service → dashboard API | `display_service.py:11` imports `_compute_*` from `dashboard.py` | Medium — layer inversion |
| framework ↔ legacy chargers | `factory.py` imports both framework and halo_adapter | Low — intentional bridge |
| solar_forecast ↔ solar_intelligence | `coordinator.py` delegates; `intelligence_bridge.py` converts | Low — explicit bridge |

No Python import cycles detected (modules import downward, not circularly). The display_service inversion is a design smell, not a runtime cycle.

---

## 10. Migration Order

```text
Step 1 (this step):
  1. Analysis report (this document)
  2. contracts/ + platform/ foundation
  3. Capability model + device registry
  4. Event bus lift + module registry
  5. Registry-based factory dispatch
  6. Decouple STALE_TELEMETRY + meter helpers
  7. Architecture tests with allowlist
  8. Vendor-neutral mocks

Step 2:
  1. Charge Amps as reference integration (full adapter → contract → feature)
  2. Extract dashboard compute from route handlers
  3. VehicleProvider factory/registry
  4. Fix display_service layer inversion
  5. Port ev_accounting to IMeterReader contract

Step 3:
  1. Mercedes integration behind VehicleProvider port
  2. Heartbeat integration consolidation
  3. Arctic Spa behind ISpaControl port
  4. Unified HealthStatus in API responses

Step 4+:
  1. Solar forecast stack unification
  2. Schema split (schemas.py → per-domain)
  3. models.py split (per-domain ORM modules)
  4. Event-driven decoupling for state changes
  5. Additional integrations (Zaptec, Tesla, etc.)
```

---

## 11. Compatibility Risks

| Change | Risk | Mitigation |
|--------|------|------------|
| Move STALE_TELEMETRY_SECONDS | Import breakage in 11 files | Re-export shim in mercedes/constants.py |
| Move MeterSnapshot helpers | Import breakage in ev_accounting | Re-export shim in meter_adapter.py |
| New contracts/ package | None — additive only | Re-exports, no moves |
| Registry factory dispatch | Behavior change if registry wrong | Same logic, different structure; existing tests |
| Delete devices/ placeholder | None — zero imports | Verified by grep |
| HealthStatus unification | API response format change | Mapping functions preserve existing values |

---

## 12. Test Strategy

### Existing coverage

- **1215** backend tests (pytest + httpx ASGI + SQLite tmp DB)
- **691** frontend tests (Vitest + React Testing Library)
- Domain-organized under `packages/energy-core/tests/{area}/`
- API route tests in `backend/tests/`
- Collector lane tests in `collector/tests/`

### Step 1 additions

1. **Architecture tests** (`tests/architecture/test_layering.py`):
   - contracts/ must not import db/, integrations/, or vendor packages
   - platform/ must not reference vendor names
   - Baseline allowlist for known existing violations (must not grow)

2. **Characterization tests** for endpoints affected by symbol moves:
   - Dashboard API (uses STALE_TELEMETRY_SECONDS)
   - Vehicle integration status/diagnostics

3. **Unit tests** for new foundation:
   - DeviceCapability enum + supports()
   - Device registry projection
   - Module registry
   - HealthStatus mapping functions
   - Event bus (lifted)
   - Mock providers

### Regression gate

Run `.\test-windows.ps1` before marking Step 1 complete. Zero test failures allowed.

---

## 13. Proposed Final Directory Structure

```text
packages/energy-core/src/energy_core/
├── contracts/                  # Pure ports — zero vendor imports
│   ├── __init__.py
│   ├── capabilities.py         # DeviceCapability enum + supports()
│   ├── health.py               # Unified HealthStatus + mappers
│   ├── telemetry.py            # STALE_TELEMETRY_SECONDS, meter helpers
│   ├── devices/
│   │   └── meter.py            # MeterSnapshot, integrate_power_kwh
│   ├── charging/
│   │   ├── charger.py          # Re-export ChargerAdapter, ChargerCapabilities
│   │   └── control.py          # Re-export IEnergyControlProvider
│   ├── energy/
│   │   ├── inverter.py         # IInverterTelemetry (NEW)
│   │   └── battery.py          # IBatteryTelemetry (NEW)
│   ├── vehicles/
│   │   └── provider.py         # Re-export VehicleProvider
│   ├── pricing/
│   │   └── providers.py        # Re-export price provider Protocols
│   ├── forecasting/
│   │   └── weather.py          # Re-export WeatherForecastProvider
│   └── spa/
│       └── control.py          # ISpaControl (NEW, stub)
│
├── platform/                   # Shared runtime — no vendor knowledge
│   ├── __init__.py
│   ├── lifecycle.py            # Register/Initialize/Start/Stop/HealthCheck
│   ├── devices/
│   │   └── registry.py         # Device registry (read projection)
│   ├── modules/
│   │   └── registry.py         # ModuleDescriptor + static registration
│   ├── health/
│   │   └── aggregator.py       # Wraps integrations/health.py
│   └── events/
│       ├── bus.py                # Lifted from charging_intelligence
│       └── types.py              # Domain event name constants
│
├── integrations/               # EXISTING — vendor adapters
│   ├── arctic_spa/
│   ├── charging_stations/chargefinder/
│   ├── health.py
│   └── collector_health.py
│
├── mocks/                      # NEW — vendor-neutral test doubles
│   ├── charger.py
│   ├── inverter.py
│   ├── battery.py
│   ├── price_provider.py
│   └── spa.py
│
└── (37 existing subpackages — unchanged, with shims where symbols move)
```

---

## 14. Proposed Interfaces / Contracts

### Existing (re-exported via contracts/)

```python
# contracts/charging/charger.py
ChargerAdapter          # from framework/models.py
ChargerCapabilities     # from framework/models.py (canonical)
ChargerController       # from chargers/base.py
MeterReader             # from framework/models.py

# contracts/vehicles/provider.py
VehicleProvider           # from vehicles/abstractions/provider.py
VehicleCommandProvider    # from vehicles/abstractions/provider.py

# contracts/charging/control.py
IEnergyControlProvider    # from energy_control/provider.py

# contracts/pricing/providers.py
IMarketPriceProvider      # from price_engine/providers/base.py
IImportPriceProvider
IExportPriceProvider

# contracts/forecasting/weather.py
WeatherForecastProvider   # from solar_forecast/weather.py
```

### New in Step 1

```python
# contracts/energy/inverter.py
class IInverterTelemetry(Protocol):
    async def get_solar_power_w(self) -> float | None: ...
    async def get_battery_soc_pct(self) -> float | None: ...
    async def get_battery_power_w(self) -> float | None: ...
    async def get_grid_power_w(self) -> float | None: ...

# contracts/energy/battery.py
class IBatteryTelemetry(Protocol):
    async def get_soc_pct(self) -> float | None: ...
    async def get_power_w(self) -> float | None: ...
    async def get_capacity_kwh(self) -> float | None: ...

# contracts/capabilities.py
class DeviceCapability(StrEnum):
    READ_POWER = "read_power"
    READ_ENERGY = "read_energy"
    START = "start"
    STOP = "stop"
    SET_CURRENT = "set_current"
    READ_BATTERY_SOC = "read_battery_soc"
    SET_CHARGE_POWER = "set_charge_power"
    SET_DISCHARGE_POWER = "set_discharge_power"
    READ_TEMPERATURE = "read_temperature"
    SET_TEMPERATURE = "set_temperature"
    # ... mapped from ChargerCapabilities booleans

def supports(caps: ChargerCapabilities, capability: DeviceCapability) -> bool: ...

# contracts/health.py
class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
```

### Capability-based interfaces (Step 2+)

Small capability ports preferred over large device interfaces:

```python
IPowerReadable          # get_power_w() -> float
IEnergyReadable         # get_energy_kwh() -> float
IStartStopControllable  # start(), stop()
ICurrentLimitControllable  # set_current(amps), get_current()
IBatterySocReadable     # get_soc_pct() -> float
IChargingControllable   # start_charging(), stop_charging()
ITemperatureReadable    # get_temperature_c() -> float
ITemperatureSetpointControllable  # set_temperature(c)
```

---

## 15. Files that should NOT yet be changed

| File | Reason |
|------|--------|
| `backend/app/schemas.py` | 1935 LOC API contract; frontend depends on field names |
| `packages/energy-core/src/energy_core/db/models.py` | 76 models, 61 migrations depend on it |
| `alembic/versions/*` | No schema changes in Step 1 |
| `vehicles/mercedes/protocol/proto/*` | Generated protobuf |
| All vendor client implementations | charge_amps.py, mercedes/*, arctic_spa/*, etc. |
| `backend/app/display_service.py` | Layer inversion documented; fix in Step 2 |
| `collector/app/collector.py` | Scheduler works; refactor in Step 2 |
| `frontend/**` | No UI changes in Step 1 |

---

## 16. Step-by-step Implementation Plan

### Phase 1: Analysis (this document) ✅

### Phase 2: Foundation packages

1. Create `energy_core/contracts/` with re-exports and new types
2. Create `energy_core/platform/` with registry, lifecycle, events, health
3. Create `energy_core/mocks/` with vendor-neutral test doubles
4. Add `tests/architecture/test_layering.py`

### Phase 3: Safe decoupling

1. Move `STALE_TELEMETRY_SECONDS` → `contracts/telemetry.py` (shim in mercedes/constants.py)
2. Move `MeterSnapshot`, `integrate_power_kwh`, `session_energy_from_meter` → `contracts/devices/meter.py` (shim in meter_adapter.py)
3. Replace if/elif with registry in `framework/factory.py` and `provider_factory.py`

### Phase 4: Verification

1. Run `.\test-windows.ps1` — all green
2. Run performance baseline comparison
3. Delete `energy_core/devices/` (verified dead)
4. Write `EMIC_MODULAR_ARCHITECTURE_STEP1_RESULT.md`

### Phase 5: Step 2 preview (not in this step)

1. Charge Amps end-to-end reference integration
2. VehicleProvider factory
3. Dashboard compute extraction
4. ev_accounting → IMeterReader port
5. Schema split planning

---

## Reference Integration for Step 2: Charge Amps

**Why Charge Amps:**
- Only live charger implementation
- Richest adapter framework (`ChargerAdapter`, `ChargerCapabilities`, catalog with 20+ vendors)
- Mock provider exists (`MockChargeAmpsController`)
- Smart charging engine already uses `ChargerAdapterFactory` + `LegacyControlBridge`
- Tests: 24 files in `tests/charging/`, factory tests, catalog tests

**Target structure:**

```text
integrations/chargeamps/
  ├── client.py          (move from chargers/client.py)
  ├── adapter.py         (move from framework/adapters/charge_amps.py)
  ├── config.py          (move from chargeamps_config.py)
  ├── meter_adapter.py   (keep ChargeAmpsMeterAdapter here)
  └── tests/

contracts/charging/charger.py  ← ChargerAdapter (already)
modules/smart_charging/        ← charging/engine.py (future)
```
