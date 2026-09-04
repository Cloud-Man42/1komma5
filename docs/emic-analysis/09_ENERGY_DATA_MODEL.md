# EMIC Energy Data Model

---

## 1. Does EMIC Have a Common Energy Model?

**Partially.** EMIC has multiple overlapping representations but **no single unified `EnergyState` consumed by all dashboards and automations**.

| Model | File | Used by |
|-------|------|---------|
| `RawEnergyReading` / `NormalizedEnergyReading` | `energy_core/domain.py` | Collector ingest |
| `EnergyReadingModel` (ORM) | `db/models.py` | Storage, history, financial stats |
| `EnergyState` | `energy/state.py` | Smart charging optimizer, policy |
| `EnergySiteSnapshot` | `energy_state/models.py` | Widget API, display service |
| `site_live_snapshots` JSON | `snapshots/writer.py` | Dashboard GET, snapshot API |
| `DashboardResponse` | `backend/app/schemas.py` | Main web dashboard |
| `DisplayOverviewResponse` | `backend/app/schemas_display.py` | Pi kiosk |
| Energy balance snapshot | `energy_balance/engine.py` | Diagnostics, reconciliation |

---

## 2. Canonical Storage: `energy_readings`

**Table:** `energy_readings` — PK `(site_id, recorded_at)`

| Field | Unit | Meaning |
|-------|------|---------|
| `solar_production_w` | W | PV production |
| `consumption_w` | W | House consumption |
| `grid_import_w` | W | Grid import (positive) |
| `grid_export_w` | W | Grid export (positive) |
| `battery_soc_pct` | % | State of charge |
| `battery_power_w` | W | Signed: + charge, − discharge |
| `ev_power_w` | W | EV charging power (optional) |
| `battery_charge_w` | W | Charge component (optional split) |
| `battery_discharge_w` | W | Discharge component (optional split) |

**Normalization:** `normalization/readings.py` — clamps negatives, validates SOC  
**Grid derivation:** When needed, derived from signed grid power in `heartbeat/readings.py`  
**Integration:** `energy/integration.py` — power→kWh, max gap 300s

---

## 3. Representation by Energy Flow

### Grid Import / Export
- **Storage:** `grid_import_w`, `grid_export_w` on readings
- **Live:** Heartbeat live overview → snapshot
- **Economics:** Import cost = import kWh × purchase price; export revenue via `export_revenue/calculator.py`
- **UI:** Energy flow diagram, Pi grid section, dashboard live metrics

### Solar Production
- **Storage:** `solar_production_w`
- **Also:** Sungrow inverter PV via energy balance (`sungrow/heartbeat_provider.py`)
- **Forecast:** `solar_forecast_*` tables, intelligence ML
- **Attribution:** Direct-to-house vs to-battery (`list_financial_stats` corrected logic per `docs/ekonomi-berakning.md`)

### Battery Charge / Discharge / SOC
- **Storage:** `battery_power_w`, `battery_soc_pct`, optional charge/discharge split columns
- **Ledger:** `battery_energy_ledger` — cumulative solar vs grid sourced battery energy
- **State enum:** `BatteryState` in `energy_state/models.py` (CHARGING, DISCHARGING, IDLE, FULL, etc.)
- **Derived in:** `energy_state/service.py` `_derive_battery_state()`

### House Consumption
- **Storage:** `consumption_w` on readings
- **Balance check:** `energy_balance/engine.py` computes `non_ev_house_load_w = consumption - ev_power`
- **Forecast:** `flexible_load/house_load.py` — hour-of-day profile from 14-day history

### EV Charging
- **Site level:** `ev_power_w` on readings; Heartbeat `evChargersAggregated`
- **Charger level:** `ev_chargers.last_actual_power_w`, sessions in `ev_charging_sessions`
- **Attribution:** 4-source split: solar_direct, solar_battery, grid_battery, grid_direct (`ev_accounting/attribution.py`)
- **Vehicle level:** Mercedes `vehicle_state_latest.charging_power_w`

### SPA Consumption
- **Storage:** `consumer_samples` via `energy_consumers` (not in site readings directly)
- **Integration:** Arctic Spa poll → consumer accounting → aggregates
- **Not merged into** `energy_readings.consumption_w` automatically — separate track

### Heating / Cooling
- **Not explicitly modeled** as separate channels in `energy_readings`
- **Partial proxy:** House consumption includes HVAC; spa has own consumer
- **Sensibo:** Not integrated — no thermostat data

### Other Loads
- **Energy balance residual:** `residual_w` when Sungrow + Halo + Heartbeat don't align
- **Flexible loads:** `flexible_load_plan` for spa scheduling

---

## 4. Runtime Decision Model: `EnergyState`

**File:** `packages/energy-core/src/energy_core/energy/state.py`

Key fields for automation:
```python
@dataclass
class EnergyState:
    timestamp: datetime
    import_price_sek_kwh: float | None
    import_price_forecast: tuple[tuple[datetime, float], ...]
    pv_power_w: float | None
    grid_import_w / grid_export_w: float | None
    home_consumption_w: float | None
    battery_power_w / battery_soc: float | None
    ev_actual_power_w / ev_target_power_w: float | None
    target_soc / deadline_at / ev_soc: ...
    stale: bool
    data_age_seconds: float
```

**Built by:** Smart charging engine from Heartbeat live overview + DB prices  
**Used by:** `charging/optimizer.py`, `charging/engine.py`, energy reasoning API

---

## 5. Widget/Display Snapshot Model

**File:** `energy_core/energy_state/models.py` — `EnergySiteSnapshot`

Structured sub-models:
- `BatteryState` enum + SOC
- `EvState` + smart charging mode/state
- `DataQuality`, `SystemStatus`
- Today energy kWh totals
- Savings SEK

**Built by:** `EnergyStateService` (`energy_state/service.py`) — DB-only, no live Heartbeat

---

## 6. Proposed Unified Model

```yaml
EnergyStateSnapshot:
  timestamp: ISO8601
  site_slug: string
  data_quality: FRESH | STALE | DEGRADED
  data_age_seconds: float

  solar:
    production_kw: float
    forecast_remaining_kwh_today: float | null

  grid:
    import_kw: float
    export_kw: float
    direction: import | export | idle

  battery:
    soc_pct: float
    power_kw: float          # + charge, - discharge
    state: charging | discharging | idle | full
    capacity_kwh: float | null

  house:
    consumption_kw: float
    non_ev_consumption_kw: float | null

  ev:
    power_kw: float
    charging: bool
    smart_mode: string | null
    sessions_active: int

  spa:
    power_kw: float | null
    enabled: bool

  prices:
    import_sek_kwh: float
    export_sek_kwh: float
    tier: green | normal | red
    strategy: string | null

  weather:
    temp_c: float | null
    cloud_cover_pct: float | null

  today:
    solar_kwh: float
    import_kwh: float
    export_kwh: float
    consumption_kwh: float
```

**Implementation path:** Extend `site_live_snapshots` JSON schema + single `GET /api/sites/{slug}/energy-state` consumed by all dashboards and Pi.

---

## 7. Model Gaps

| Gap | Impact |
|-----|--------|
| SPA not in site readings | House consumption doesn't separate spa |
| No heating/cooling channel | Can't optimize HVAC |
| Dual price stores (hourly + 15-min) | Economics may use wrong granularity |
| Dashboard vs EnergyState field names differ | Frontend mapping duplication |
| Vehicle EV power vs charger power reconciliation | Energy balance residual warnings |
| No unified forecast attachment | Solar/load/price forecasts in separate APIs |

---

## 8. Energy Balance Reconciliation

**File:** `energy_core/energy_balance/engine.py`

Correlates:
- Sungrow inverter telemetry
- Halo charger power
- Virtual EVSE reported power
- Heartbeat observed EV + home consumption

Output: `energy_balance_snapshots` with `residual_w`, alignment flags, double-counting detection (`DOUBLE_COUNTING_TOLERANCE_W` default 800W).

This is the **closest thing to a validated unified model** but only used for diagnostics, not main dashboards.

---

## 9. Identity Constraint (Economics)

Per `docs/ekonomi-berakning.md`:
```
solar_self + battery_self + imported == consumption  (per day/period)
```

Corrected attribution avoids double-counting solar→battery→house path.
