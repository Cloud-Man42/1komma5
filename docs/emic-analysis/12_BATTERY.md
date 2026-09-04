# EMIC Battery Intelligence

---

## 1. Battery Data Sources

| Source | Fields | File |
|--------|--------|------|
| Heartbeat readings | `battery_soc_pct`, `battery_power_w`, charge/discharge split | `energy_readings` |
| Sungrow (via Heartbeat) | Inverter battery telemetry | `sungrow/heartbeat_provider.py` |
| Energy balance | Battery alignment vs Halo/Heartbeat | `energy_balance/engine.py` |
| Battery ledger | Cumulative solar vs grid sourced energy | `battery_energy_ledger` |
| EnergyState | SOC, power for charging decisions | `energy/state.py` |

---

## 2. SOC Handling

| Aspect | Implementation |
|--------|---------------|
| Storage | `battery_soc_pct` on each reading (0–100) |
| Normalization | Clamped in `normalization/readings.py` |
| Full detection | SOC ≥ 99% + power deadband ≤25W → `BatteryState.FULL` |
| Stale detection | Via reading age in dashboard (`STALE_SECONDS` in dashboard.py) |
| Widget text | `battery_state_text_sv()` in `energy_state/models.py` |

**Min/max SOC limits for optimization:** Not configured in EMIC — assumed managed by Heartbeat/inverter.

---

## 3. Charge / Discharge Limits

| Limit | EMIC behavior |
|-------|---------------|
| Power deadband | 25W (`_POWER_DEADBAND_W` in energy_state/service.py) |
| Max charge/discharge rate | Not modeled — uses observed power only |
| Grid charging limit | Not explicitly constrained in EMIC optimizer |
| Export limit | Observed via `grid_export_w` |

**Battery control commands:** Not sent by EMIC directly — monitoring and EV-charging-side logic only.

---

## 4. Battery Energy Ledger

**Table:** `battery_energy_ledger`  
**File:** `ev_accounting/battery_ledger.py`

Tracks cumulative:
- `solar_energy_kwh` — battery charged from solar
- `grid_energy_kwh` — battery charged from grid
- `grid_energy_cost_sek` — cost of grid-sourced battery energy

Used for EV attribution (solar_battery vs grid_battery paths) and economics.

---

## 5. Battery in Economics

| Path | Treatment |
|------|-----------|
| Solar → battery → house | Battery discharge credited as battery savings (not solar direct) |
| Grid → battery → house | Battery savings at purchase price; grid cost already counted on import |
| Solar → battery (not yet discharged) | Not counted as solar savings until discharge |
| Battery export to grid | Via `grid_export_w`; export revenue applies |

See `docs/ekonomi-berakning.md` for corrected attribution (fixed solar-via-battery double count).

---

## 6. Battery in Smart Charging

`EnergyState` includes:
- `battery_power_w`, `battery_soc`
- Used to decide: wait for solar surplus, avoid grid charging during expensive periods
- Export hysteresis: reason codes `waiting_for_export`, `export_hysteresis`

**Not used for:** Direct battery charge/discharge scheduling.

---

## 7. Battery in Forecasting

| Forecast | Battery role |
|----------|-------------|
| Solar forecast | Predicts surplus for potential battery charging |
| Load forecast | House load affects net grid need |
| Seasonal year forecast | `BATTERY_PROFILE` monthly shape in `forecasting.py` |
| Forecast learning | Kind `load_w` — indirect |

**No dedicated battery SOC forecast.**

---

## 8. Battery Opportunity Engine (Proposed)

Using **existing EMIC data**:

| Input | Source |
|-------|--------|
| Nord Pool / import price | `price_periods` via price_engine |
| Export price | `price_periods.export_price_sek_kwh` |
| Solar forecast | `solar_forecast_points` / intelligence |
| Load forecast | `flexible_load/house_load.py` |
| Weather | `solar_weather_cache` |
| Historical usage | `energy_readings`, `energy_daily` |
| Battery SOC | Latest reading |
| Battery capacity | Site config or default 13.5 kWh (display service default) |

**Decisions to compute:**
1. Charge from solar now vs later
2. Discharge to house vs export during peak price
3. Grid charge during cheap window vs preserve SOC
4. Reserve SOC for evening peak vs EV charging need

**Output:** Recommendation API → energy_control apply → Heartbeat battery mode (if supported)

**Complexity:** MEDIUM — data exists; needs optimization logic + Heartbeat write path.

---

## 9. Gaps

| Gap | Impact |
|-----|--------|
| No min/max SOC config in EMIC | Can't enforce reserve for outages |
| No battery capacity in site config (uses default) | SOC→kWh conversion approximate |
| No direct battery control | EMIC is monitor, not actuator for battery |
| No degradation cost model | Arbitrage ROI overstated |
| No battery-specific forecast | Can't plan overnight SOC target |

---

## 10. Pi / Dashboard Battery Display

- No standalone battery route on web — embedded in Energy + Overview
- Pi section: `/display/[slug]/battery`
- Phase 2 gaps per `docs/PI_KIOSK.md`: charge/discharge today curve not yet in display API

---

## 11. UNKNOWN

- Actual installed battery capacity at production sites
- Heartbeat/Sungrow battery control API capabilities
- User-configured SOC limits in Heartbeat app vs EMIC
