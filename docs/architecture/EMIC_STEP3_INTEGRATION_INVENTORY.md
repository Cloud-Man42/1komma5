# EMIC Step 3 – Integration Inventory

**Date:** 2026-09-07  
**Baseline tests:** Python + frontend suite green (705 frontend; full `test-windows.ps1` PASS)

---

## Dependency Graph (Integration → Capability → Feature → API)

```
integration.heartbeat
  → ENERGY_READ_*, BATTERY_READ_*, PRICE_READ_*
  → feature.price-engine, feature.energy-balance, feature.smart-charging, feature.energy-control
  → dashboard, snapshot, EV bridge, economics

integration.chargeamps
  → EV_CHARGER_*
  → feature.smart-charging, feature.energy-balance
  → EvOverview, EvDiagnosticsPanel, charging API

integration.mercedes
  → VEHICLE_READ_*
  → feature.vehicles, feature.smart-charging (optional)
  → vehicles API, Mercedes admin UI

integration.arctic_spa
  → SPA_READ_TEMPERATURE, READ_POWER
  → feature.spa-energy
  → spa API, SpaHealthPanel

integration.chargefinder
  → READ_STATUS
  → charging intelligence station resolver
  → admin chargefinder page

integration.smhi / integration.dmi / integration.open_meteo
  → WEATHER_READ_*
  → feature.solar-forecast
  → solar intelligence API/UI

feature.price-engine (Nord Pool via Heartbeat proxy)
  → PRICE_READ_*
  → smart charging economics, PriceChart
```

---

## Integration Table

| Integration | Current location | ModuleId | Protocol | Auth | Sites | Migration status | Migration risk |
|-------------|------------------|----------|----------|------|-------|------------------|----------------|
| 1Komma5 Heartbeat | `integrations/heartbeat/`, `providers/heartbeat_wiring.py` | `integration.heartbeat` | REST | OAuth/token | All with external_system_id | **STANDARDIZED** (Step 3.1) | HIGH |
| Charge Amps | `integrations/chargeamps/`, `chargers/framework/adapters/charge_amps.py` | `integration.chargeamps` | REST | API key | Åkarp (bridge) | **PARTIAL** → STANDARDIZED via adapter factory | HIGH (control) |
| Mercedes-Benz | `integrations/mercedes/`, `vehicles/mercedes/` | `integration.mercedes` | REST/WS | OAuth | Åkarp | **PARTIAL** (supervisor lifecycle OK; domain layer shrink ongoing) | MEDIUM |
| Arctic Spa | `integrations/arctic_spa/`, `spa_energy/` | `integration.arctic_spa` | REST | Token | Config sites | **STANDARDIZED** (lane gating + factory) | LOW |
| Nord Pool (via Heartbeat) | `price_engine/providers/heartbeat_market.py` | `feature.price-engine` | Proxied | Heartbeat | All | **STANDARDIZED** (provider_resolver) | MEDIUM |
| Sungrow (via Heartbeat) | `sungrow/`, `integrations/heartbeat/telemetry.py` | (under heartbeat) | Proxied | Heartbeat | Åkarp | **PARTIAL** (normalization layer exists) | LOW |
| SMHI | `solar_intelligence/providers/smhi_*.py` | `integration.smhi` | REST | Public | SE sites | **STANDARDIZED** (module descriptor) | LOW |
| DMI Harmonie | `solar_intelligence/providers/dmi_harmonie.py` | `integration.dmi` | REST | Public | DK sites | **STANDARDIZED** (module descriptor) | LOW |
| Open-Meteo | `solar_forecast/open_meteo.py` | `integration.open_meteo` | REST | Optional key | Fallback | **STANDARDIZED** (module descriptor) | LOW |
| ChargeFinder | `integrations/charging_stations/chargefinder/` | `integration.chargefinder` | Web scrape | Session | Global | **STANDARDIZED** (bootstrap + lane gate) | LOW |
| Zaptec | `integrations/zaptec/` | — | REST | Token | — | **SCAFFOLD** (mock default) | LOW |
| Tesla | `integrations/tesla/` | — | REST | OAuth | — | **SCAFFOLD** (mock default) | LOW |
| Sensibo | — | — | — | — | — | **PLANNED** | — |
| Ebeco/EB500 | — | — | — | — | — | **PLANNED** | — |
| Gecko | — | — | — | — | — | **PLANNED** | — |
| FoxESS | — | — | — | — | — | **NOT FOUND** | — |
| gridX | Heartbeat discovery metadata | — | — | — | EV sync | **ALREADY COMPLIANT** (metadata only) | INFO |

---

## Vendor Leak Classification (Hotspots)

| Location | Classification | Severity | Step 3 action |
|----------|----------------|----------|-------------|
| `charging/engine.py` | Was FEATURE LEAK → **FIXED** via `resolve_energy_state_provider` | — | Done |
| `charging/reasoning.py` | Was FEATURE LEAK → **FIXED** via provider_resolver | — | Done |
| `price_engine/engine.py` | VALID (uses registry wiring) | INFO | provider_resolver added for capability path |
| `energy_control/heartbeat_provider.py` | VALID ADAPTER | LOW | Remains in energy_control wiring |
| `vehicles/mercedes/*` | VALID INTEGRATION (vendor-internal) | INFO | Domain imports via `integrations/mercedes/factory` |
| `vehicles/commands/service.py` | FEATURE LEAK (Mercedes-specific) | MEDIUM | Deferred: uses factory boundary |
| `charging/readiness.py` | VALID (charger framework readiness) | INFO | Uses `build_chargeamps_readiness` in framework |
| `solar_intelligence/provider_factory.py` | VALID ADAPTER (country router) | INFO | Weather modules registered separately |
| `spa_energy/*` | ALREADY COMPLIANT | INFO | Uses `providers/spa.py` wiring |

---

## Runtime Workers

| Worker | Owner module | Lifecycle |
|--------|--------------|-----------|
| Collector fast lane (Heartbeat fetch) | `integration.heartbeat` | Lane gating |
| Smart charging engine | `feature.smart-charging` | Lane gating |
| Mercedes supervisor | `integration.mercedes` | Orchestrator handler |
| Arctic spa polling | `integration.arctic_spa` | Lane gating |
| ChargeFinder health probe | `integration.chargefinder` | Lane gating (Step 3.6) |
| Solar forecast | `feature.solar-forecast` | Lane gating |

---

## Database Ownership

| Data | Classification |
|------|----------------|
| `ev_chargers`, chargeamps credentials | Integration configuration |
| `vehicle_provider_connections` | Integration configuration |
| `energy_readings` | Normalized EMIC data |
| `vehicle_charge_sessions` | Feature-derived data |
| `price_periods` | Normalized EMIC data |
| Historical energy | **Preserved — no schema destructive changes in Step 3** |
