# EMIC Smart Energy Management

Assessment of existing automation vs target EMS capabilities.

---

## 1. Feature Matrix (What Exists)

| Capability | Status | Implementation |
|------------|--------|----------------|
| **Solar forecasting** | ✅ Production | `solar_forecast/`, `solar_intelligence/` — physical + ML, 48h horizon |
| **Load forecasting** | ⚠️ Basic | `flexible_load/house_load.py` — 14-day hour-of-day profile |
| **Price forecasting** | ⚠️ Implicit | Price engine stores actual 15-min; forecast_learning records predictions |
| **Battery optimization** | ⚠️ Partial | Energy control interface; no full arbitrage engine |
| **EV optimization** | ✅ Production | `charging/optimizer.py`, smart schedule, solar charging plan |
| **Price optimization** | ✅ Production | Smart charging modes: PRICE_CHARGE, SOLAR_CHARGE, SMART_CHARGE |
| **Weather optimization** | ⚠️ Input only | Weather feeds solar forecast; not load/HVAC |
| **SPA scheduling** | ✅ Production | `spa_energy/service.py`, flexible load planner, filter schedule |
| **Heating scheduling** | ❌ Missing | No Sensibo/HVAC integration |
| **Cooling scheduling** | ❌ Missing | No integration |
| **Energy orchestration** | ⚠️ Config only | Priority settings API; limited auto-action |
| **Forecast learning** | ✅ Production | Predict vs actual for price, load, solar |
| **Energy control** | ⚠️ New | `energy_control/` — sync from price strategy; `optimization_mode` on site |

---

## 2. Decision Capability Assessment

### "When should the battery charge?"
| Aspect | Current | Gap |
|--------|---------|-----|
| From solar surplus | Observed via readings; smart EV charging waits for export | Battery control not exposed — **Heartbeat may control battery, EMIC monitors only** |
| From grid (cheap hours) | Price engine identifies cheap periods; energy_control can sync actions | No automated grid-charge command unless via Heartbeat bridge |
| **Verdict** | **Monitor + partial recommend** | No Battery Opportunity Engine |

### "When should the battery sell/discharge?"
| Aspect | Current | Gap |
|--------|---------|-----|
| Export during peak prices | Price strategy shows tiers; energy_control preview/apply | Actual battery dispatch depends on Heartbeat/inverter — EMIC doesn't directly control Sungrow battery |
| **Verdict** | **Informational only** | Needs inverter control integration |

### "When should the car charge?"
| Aspect | Current | Gap |
|--------|---------|-----|
| Smart modes | ✅ SmartChargingEngine with PRICE_CHARGE, SOLAR_CHARGE, SMART_CHARGE, export hysteresis | — |
| Vehicle SOC/deadline | ✅ Mercedes integration provides target_soc, departure | — |
| Solar plan | ✅ `/solar-charging-plan` endpoint | — |
| **Verdict** | **Production-ready** | Best-automated load |

### "When should SPA heat?"
| Aspect | Current | Gap |
|--------|---------|-----|
| Filter schedule optimization | ✅ `spa_energy/filter_schedule_service.py` | — |
| Price-aware planning | ✅ Flexible load plan blocks | — |
| Shadow mode | ✅ `/spa/shadow` — dry run | — |
| **Verdict** | **Production-ready** (if Arctic Spa enabled) | — |

### "When should house heat/cool?"
| **Verdict** | **Not implemented** | No thermostat integration |

### "When to use heat pump?"
| **Verdict** | **Not implemented** | Consumption visible but no control |

### "Buy cheap grid vs use battery?"
| Aspect | Current | Gap |
|--------|---------|-----|
| Price comparison | Price engine current/today/tomorrow; energy strategy card | No unified arbitrage decision |
| Battery SOC consideration | In EnergyState for EV charging, not house battery arbitrage | — |
| **Verdict** | **Data available, decision not automated** | Battery Opportunity Engine needed |

---

## 3. Smart Charging Engine Detail

**File:** `energy_core/charging/engine.py`, `optimizer.py`

Modes (mapped from Heartbeat):
- PAUSED, QUICK_CHARGE, PRICE_CHARGE, SOLAR_CHARGE, SMART_CHARGE

Decision inputs (`EnergyState`):
- Import price + forecast
- PV power, grid import/export
- Battery SOC/power
- EV power, target SOC, deadline
- Vehicle linked state

Outputs:
- Charge Amps current control
- `ev_bridge_cycles` logging
- Energy reasoning text for UI

States include: `WAITING_FOR_SURPLUS`, export hysteresis, solar forecast wait.

---

## 4. Energy Control Interface

**Migration:** 057_energy_control_interface  
**Files:** `energy_core/energy_control/service.py`, `backend/app/api/energy_control.py`

- Site flag: `energy_control_enabled`, `optimization_mode` (MONITOR_ONLY vs active)
- Collector syncs from price strategy snapshot
- API: status, settings, preview, apply, recent actions
- **Provider pattern:** `energy_control/provider.py` — extensible to Heartbeat commands

**Current scope:** Early stage — sync from strategy, not full closed-loop optimization.

---

## 5. Energy Orchestration

**API:** `GET/PUT /api/sites/{slug}/energy/orchestration`

- Priority ordering between loads (EV, spa, battery)
- UI panel: `EnergyOrchestrationPanel.tsx`
- **Limited automatic enforcement** — mostly configuration

---

## 6. Price Engine Strategy

**Files:** `price_engine/strategy.py`, `strategy_service.py`

- Computes current energy strategy from price periods
- Tiers: green/normal/red
- Exposed: `/energy-strategy/current`, sidebar card
- Feeds energy_control collector sync

---

## 7. What's Required for Full EMS

| Layer | Requirement | EMIC status |
|-------|-------------|-------------|
| Unified EnergyState | Single snapshot for all decisions | Partial |
| Forecast bundle | Solar + load + price horizons | Partial (3 separate systems) |
| Optimization engine | LP/heuristic scheduler for loads + battery | EV + SPA only |
| Actuator layer | Commands to inverter, HVAC, charger | Charger + SPA + vehicle; not battery/HVAC |
| Closed-loop learning | Forecast learning → auto-adjust params | Recording only, no auto-tune |
| Safety constraints | Min SOC, max grid import, user overrides | Partial (EV deadlines, spa safe schedule) |

---

## 8. Realistic Next Steps (from existing code)

1. **Battery Opportunity Engine** — combine price_engine + solar forecast + EnergyState + battery SOC (read-only recommendations first)
2. **Close forecast learning loop** — auto-adjust correction factors (infra exists in solar forecast)
3. **Extend energy_control** — Heartbeat battery mode commands via existing bridge
4. **Unified scheduler** — merge EV optimizer + spa planner + energy_control into single horizon optimizer (`flexible_load/horizon.py` exists)

---

## 9. UNKNOWN

- Whether Heartbeat API supports battery mode write commands at production sites
- User adoption of energy_control apply vs preview-only
- EMS shadow simulation output usage (`collector._run_ems_shadow_simulation`)
