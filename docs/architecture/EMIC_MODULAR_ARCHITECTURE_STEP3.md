# EMIC Modular Architecture — Step 3

Step 3 standardizes external integrations behind vendor-neutral capabilities while preserving existing production behavior.

## 1. Golden Rule

EMIC Core and Feature Modules must not contain vendor-specific business logic. Features request capabilities:

```text
Give me a provider for Capability.X
```

not:

```text
Is Charge Amps enabled? Use HeartbeatClient...
```

## 2. Integration Module Structure

```text
Integration Module
 ├── Descriptor (bootstrap.py)
 ├── Configuration (existing DB tables)
 ├── Client (vendor protocol only)
 ├── Adapter (vendor DTO → EMIC model)
 ├── Runtime Handler (or LaneModuleHandler)
 ├── Capability Providers (orchestrator register/unregister)
 ├── Health Provider
 └── Tests
```

## 3. Runtime Ownership (Step 3.0)

```text
Collector = authority for actual module runtime
Backend/API = reads distributed state from Redis
```

Flow:

```text
ModuleOrchestrator transition
  → Redis key emic:runtime:{site_id}:{module_id} (TTL 90s)
  → SiteModuleResolver reads Redis for API projection
  → Periodic reconcile (120s) compares DB desired vs collector registry
```

Stale collector: TTL expiry → API shows non-RUNNING (never false RUNNING).

## 4. Capability Model

Reuse [`Capability`](../../packages/energy-core/src/energy_core/platform/capabilities/types.py) enum and [`CapabilityRegistry`](../../packages/energy-core/src/energy_core/platform/capabilities/registry.py).

Read vs control separated:

- `EV_CHARGER_READ_*` vs `EV_CHARGER_START/STOP/SET_CURRENT`
- `ENERGY_READ_*` vs write controls in energy_control

## 5. Provider Resolution

| Domain | Resolver | Path |
|--------|----------|------|
| Energy state | `energy/provider_resolver.py` | Capability → Heartbeat adapter (extensible) |
| Price | `price_engine/provider_resolver.py` | Capability → Heartbeat market/export |
| EV charger | `ChargerAdapterFactory` | Device model → adapter |
| Vehicle | `vehicles/provider_factory.py` | Site connection → provider |
| Spa | `providers/spa.py` | Factory wiring |
| Charging stations | `providers/charging_stations.py` | ChargeFinder provider |

## 6. Error Model

Vendor exceptions mapped at integration boundary. Features consume normalized failures via contracts and degraded states.

## 7. Health

Separate from enabled/runtime:

```text
Enabled = true, Runtime = RUNNING, Health = DEGRADED  ← valid
```

## 8. Secrets

Credentials stay in encrypted DB fields. Never in module descriptors, API responses, or logs.

## 9. Migration Strategy

One integration at a time:

```text
Baseline → Characterization tests → Migration → Tests → Legacy removal → Gate
```

Migration order (dependency-driven):

1. Step 3.0 runtime status sync
2. Heartbeat
3. Price/Nord Pool
4. Charge Amps
5. Mercedes
6. Weather (SMHI/DMI/Open-Meteo)
7. ChargeFinder
8. Arctic Spa formalization
9. Sungrow normalization

## 10. Non-Goals

- Step 4 Module Manager UI
- New integrations not in codebase (Sensibo, Ebeco, direct Nord Pool)
- Algorithm rewrites
- Destructive historical data migration
