# EMIC Forecasting

---

## 1. Solar Forecast

### 1.1 Architecture

| Layer | Path | Role |
|-------|------|------|
| Coordinator | `solar_forecast/coordinator.py` | Refresh scheduling, retention |
| Physical model | `solar_forecast/physical.py`, `engine.py` | PV production from radiation |
| Weather routing | `routing_weather.py`, `open_meteo.py`, `dmi_weather.py` | Multi-provider weather |
| Correction | `correction.py` | EMA correction factor from observations |
| Extended | `extended_forecast.py` | Up to 7 days |
| Intelligence ML | `solar_intelligence/` | Training samples, model records, hourly forecast |

### 1.2 Configuration

| Setting | Default | Env var |
|---------|---------|---------|
| Horizon | 48h | `SOLAR_FORECAST_HORIZON_HOURS` |
| Extended days | 7 | `SOLAR_FORECAST_EXTENDED_DAYS` |
| Refresh | 30 min | `SOLAR_FORECAST_REFRESH_MINUTES` |
| Retention | 14 days | `SOLAR_FORECAST_RETENTION_DAYS` |
| Weather cache | 45 min | `SOLAR_WEATHER_CACHE_MINUTES` |

### 1.3 Storage

- `solar_forecast_runs`, `solar_forecast_points` — run output
- `solar_forecast_observations` — actual vs predicted
- `solar_forecast_evaluations` — accuracy metrics
- `solar_forecast_hourly`, `solar_daily_forecast_snapshots` — intelligence layer
- `solar_training_samples`, `solar_models` — ML pipeline

### 1.4 API Endpoints

- `/solar/forecast`, `/today`, `/tomorrow`
- `/solar/accuracy`, `/diagnostics`, `/energy-budget`
- `/solar/intelligence/forecast`, `/train`, `/backfill`
- `/solar/model/metrics`

---

## 2. Consumption (Load) Forecast

**File:** `flexible_load/house_load.py`

- Builds hour-of-day profile from **14 days** of `energy_readings`
- Used by: spa planner, flexible load horizon
- **Not exposed** as standalone dashboard forecast API

**Forecast learning kind:** `load_w` — records predicted vs actual in `energy_forecast_snapshots`

---

## 3. Price Forecast

**Not a statistical forecast model.**

- Actual prices stored in `price_periods` (15-min) from Heartbeat
- Price engine provides today/tomorrow via `/price-engine/today`, `/tomorrow`
- Forecast learning kind: `import_price_sek_kwh` — compares predictions to actuals
- **Prediction source for learning:** UNKNOWN exact model — recorded in forecast_learning service

---

## 4. EV Usage Forecast

- **Smart schedule:** `charging/smart_schedule.py` — uses price + solar plan + deadline
- **Solar charging plan:** `/ev-chargers/{id}/solar-charging-plan`
- **Vehicle required energy:** Computed from target SOC in `EnergyState`
- **No long-term driving pattern forecast**

---

## 5. Accuracy Metrics

### 5.1 Solar

| Metric | Location |
|--------|----------|
| MAPE | `solar_forecast/` evaluation; config `SOLAR_FORECAST_MAPE_MIN_ACTUAL_KWH` |
| Calibration tiers | PRELIMINARY (7 samples), CALIBRATED (30), MATURE (60) |
| Correction factor | EMA alpha 0.15, bounds 0.70–1.30 |
| API | `/solar/accuracy`, `/solar/model/metrics` |

**Production MAPE/MAE/Bias logging:** Not found in structured prod metrics — available via API diagnostics. **Production values: UNKNOWN.**

### 5.2 Forecast Learning

**File:** `forecast_learning/service.py`

Records for kinds:
- `import_price_sek_kwh`
- `load_w`
- `solar_w`

API: `/forecast-learning/summary`, `/recent`

**Does not auto-adjust models** — recording only.

---

## 6. Why Forecasts Can Be Wrong

| Cause | Affected forecast | Mitigation in code |
|-------|-------------------|-------------------|
| Weather provider outage | Solar | Multi-provider routing; LKG degraded mode |
| Wrong site location/config | Solar | `solar_site_configurations`, array models |
| Insufficient training samples | Solar ML | Tier system (preliminary/calibrated/mature) |
| Season change | Solar correction | Rolling 60-day window; EMA correction |
| Snow/soiling not modeled | Solar | SMHI snow provider; manual correction factor |
| Cloud timing error | Solar intraday | Observation evaluation in collector |
| Heartbeat price delay | Price | Fallback purchase price |
| EV schedule unpredictability | Load | Deadline-based, not pattern-based |
| SPA manual override | Load | Shadow mode |
| Missing HVAC data | Load | Not in model |

---

## 7. Adaptive / Self-Learning Potential

| Capability | Exists | Auto-applied |
|------------|--------|--------------|
| Solar correction EMA | ✅ | ✅ in forecast engine |
| Solar ML retrain | ✅ `/intelligence/train` | Manual trigger |
| Forecast learning recording | ✅ | ❌ no feedback loop |
| Seasonal model switching | ❌ | — |
| Weather-normalized regression | ⚠️ Partial in intelligence | — |
| Price prediction model | ❌ | — |
| Load ARIMA/neural | ❌ | — |

---

## 8. Recommendations

1. **Close the loop:** forecast_learning → auto-adjust correction factor (infra exists)
2. **Solar forecast snapshot** for GET performance (critical)
3. **Expose load forecast** API from existing `house_load.py`
4. **Log MAPE daily** to `solar_performance_daily` (table exists) and surface in UI
5. **Seasonal models:** train separate winter/summer correction profiles (data in training samples)

---

## 9. UNKNOWN

- Production MAPE values over last 30 days
- Whether intelligence ML model is trained in production or physical-only
- Forecast learning prediction algorithm details
