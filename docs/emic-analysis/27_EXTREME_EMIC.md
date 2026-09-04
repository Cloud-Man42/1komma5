# Extreme EMIC — Advanced EMS Gap Analysis

What EMIC needs to become an **extremely advanced Energy Management System**, grounded in what the codebase already has vs what is missing.

---

## 1. Current EMIC Maturity

EMIC today is best described as:

> **Advanced energy monitor + partial load optimizer**

| EMS capability | Maturity (1–5) | Evidence |
|----------------|----------------|----------|
| Monitoring | 5 | Full dashboards, Pi, widgets, snapshots |
| Data ingestion | 4 | Collector-centralized, resilient |
| Economics | 4 | Corrected attribution, export revenue |
| Solar forecasting | 4 | Physical + ML, correction EMA |
| EV optimization | 4 | Smart charging engine, multiple modes |
| SPA optimization | 3 | Flexible load planner, shadow mode |
| Price optimization | 3 | Price engine, strategy tiers |
| Battery optimization | 1 | Monitor only, no actuation |
| Load forecasting | 2 | Hour-of-day profile only |
| HVAC optimization | 0 | No integration |
| Learning / adaptation | 2 | Records forecasts, limited auto-tune |
| Automation / actuation | 2 | EV + spa; not battery/HVAC |
| Multi-load coordination | 2 | Orchestration config, not enforced |
| Arbitrage | 1 | Data exists, no decision engine |

---

## 2. Gap Analysis by Intelligence Domain

### Prediction
| Need | Have | Missing |
|------|------|---------|
| Solar production forecast | ✅ 48h + 7d, ML pipeline | Intraday confidence intervals on overview |
| Consumption forecast | ⚠️ Basic diurnal | ML model, weather-normalized load |
| Price forecast | ⚠️ Actuals stored | Statistical forward model |
| EV driving forecast | ❌ | Pattern from vehicle history |
| Battery SOC forecast | ❌ | SOC trajectory given plans |
| Unified forecast bundle | ❌ | Single horizon object for optimizer |

### Optimization
| Need | Have | Missing |
|------|------|---------|
| EV charge scheduling | ✅ Smart charging engine | — |
| SPA filter/clean scheduling | ✅ Spa energy service | — |
| Battery charge/discharge schedule | ❌ | LP/MILP optimizer |
| Multi-load joint schedule | ❌ | Horizon optimizer across loads |
| Grid import limit respect | ⚠️ Phase current in EnergyState | Hard constraint enforcement |
| User preference constraints | ⚠️ Deadlines, target SOC | Comfort bounds for HVAC |

### Automation
| Need | Have | Missing |
|------|------|---------|
| EV current control | ✅ Charge Amps writes | — |
| SPA actuator control | ✅ Arctic Spa commands | — |
| Battery mode control | ❌ | Heartbeat/inverter write path |
| HVAC control | ❌ | Sensibo or equivalent |
| Automated apply (not preview) | ⚠️ energy_control early | User trust + safety guardrails |
| Rollback on failure | ⚠️ Spa safe schedule restore | General automation rollback |

### Learning
| Need | Have | Missing |
|------|------|---------|
| Solar correction EMA | ✅ | — |
| Forecast error recording | ✅ forecast_learning | — |
| Auto parameter tuning | ❌ | Close loop from learning |
| Seasonal model selection | ❌ | Winter/summer profiles |
| User behavior learning | ❌ | Adapt to household patterns |
| Model retrain automation | ⚠️ Manual `/intelligence/train` | Scheduled retrain |

---

## 3. Realistic Extreme EMIC Vision

An "extreme" but **achievable** EMIC within 12–18 months on current architecture:

### Layer 1: Unified Brain
- Single `EnergyStateSnapshot` updated every collector cycle
- All dashboards, Pi, widgets, automations read one source
- Redis-backed with SSE push

### Layer 2: Prediction Engine
- Solar: existing pipeline + auto correction from learning
- Load: ML model trained on readings + weather + day-type
- Price: forward curve from historical + Heartbeat tomorrow
- Bundle: 48h horizon JSON attached to every snapshot

### Layer 3: Optimization Engine
- **Horizon scheduler** (24–48h): jointly optimizes EV charge windows, spa cycles, battery charge/discharge
- Respects: user deadlines, min SOC, max grid import, price tiers
- Outputs: recommended schedule + confidence + savings estimate
- Shadow mode default → user enables auto-apply per load type

### Layer 4: Actuation Layer
- EV: existing Charge Amps ✅
- SPA: existing Arctic Spa ✅
- Battery: Heartbeat battery mode commands (if API confirmed)
- HVAC: Sensibo integration (new)
- Vehicle: Mercedes start/stop ✅

### Layer 5: Learning Loop
- Nightly: compare forecast_learning errors → adjust parameters
- Weekly: retrain solar ML if enough samples
- Monthly: report accuracy trends to user

---

## 4. What EMIC Should NOT Try (Unrealistic)

- Competing with utility SCADA systems
- Sub-second real-time grid frequency control
- Custom hardware firmware (inverter internals)
- Full home automation hub replacement (lighting, security)
- Trading on Nord Pool directly without certified market access

---

## 5. Missing Integrations for Extreme EMS

| Integration | Purpose | Priority |
|-------------|---------|----------|
| Heartbeat battery write | Battery arbitrage | HIGH (if API exists) |
| Sensibo / heat pump API | HVAC load shifting | HIGH |
| Calendar API | Occupancy prediction | MEDIUM |
| Weather nowcast | Intraday solar correction | MEDIUM |
| Grid tariff API (effekttariff) | Peak shaving | MEDIUM |
| Stripe/billing | SaaS model | LOW (not in codebase) |

---

## 6. Decision Questions — Extreme Answers

| Question | Today | Extreme EMIC |
|----------|-------|--------------|
| When charge battery? | User/Heartbeat decides | Optimizer: solar surplus + cheap grid windows |
| When sell battery energy? | Not managed | Export during peak price if SOC > reserve |
| When charge car? | Smart engine ✅ | Joint optimize with battery + spa |
| When heat spa? | Spa planner ✅ | Price-aware + solar surplus |
| When heat house? | Manual thermostat | Price + forecast + comfort bounds |
| Heat pump vs cheap grid? | Not modeled | COP-aware economic comparison |
| Buy grid vs use battery? | Not computed | Marginal cost comparison each 15-min |

---

## 7. Infrastructure Requirements for Extreme EMS

| Requirement | Current | Needed |
|-------------|---------|--------|
| Decision latency | 30–60s collector | Acceptable for home EMS |
| Optimization compute | In collector loop | Dedicated optimizer task (<5s budget) |
| State storage | PostgreSQL | Same + Redis hot state |
| Push to clients | HTTP poll | SSE/WebSocket |
| Safety | Partial | Hard limits, dry-run default, rollback |
| Audit trail | energy_control_actions | Full decision log with inputs |

---

## 8. Roadmap Summary

```
Today          → 6 months        → 12 months       → 18 months
Monitor        Unified State     Horizon Optimizer  Full EMS
EV smart       Battery advisor   Battery actuation  HVAC integration
Solar forecast Learning loop     Auto-tune          User automation rules
Partial spa    Pi complete       Shadow → auto      Grid peak management
```

---

## 9. Success Metrics for "Extreme"

| Metric | Target |
|--------|--------|
| Solar forecast MAPE | <15% daily (track via existing accuracy API) |
| EV charging cost vs naive | >20% savings (already partially measured) |
| Battery arbitrage savings | Quantified SEK/month |
| Automation uptime | >99% without user intervention |
| Data freshness | Snapshot age <60s p99 |
| User comprehension | 3-second status on overview |

---

## 10. UNKNOWN

- Heartbeat API full write capability for battery modes
- Regulatory constraints on automated grid export in SE
- User willingness for full automation vs advisory mode
- Production site count for multi-tenant scaling needs
