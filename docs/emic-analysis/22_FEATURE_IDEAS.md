# EMIC Feature Ideas

Based on existing EMIC capabilities and data. Categorized by implementation scope.

---

## QUICK WIN

| NAME | WHAT | WHY | DATA REQUIRED | COMPLEXITY | USER VALUE |
|------|------|-----|---------------|------------|------------|
| Economy auto-refresh | Fix missing setInterval in economy hook | Stale cost data | financial-stats API | LOW | HIGH |
| Integration health strip | Overview badge: Heartbeat/snapshot age | 3-second system status | readiness + audit + snapshot | LOW | HIGH |
| Best charge window | Card showing cheapest 4h today/tomorrow | EV planning | price_engine (already in sidebar) | LOW | HIGH |
| Yesterday comparison | "vs igår" on today kWh | Context without navigation | energy_daily rollup | LOW | MEDIUM |
| Forecast accuracy on solar | Move accuracy widget to solar overview | Trust in forecasts | solar/accuracy API | LOW | MEDIUM |
| Snapshot age badge | Global freshness indicator | Know when data is stale | dashboard/snapshot generated_at | LOW | HIGH |
| Battery source split | Show solar vs grid charged kWh | Understand battery economics | battery_energy_ledger | LOW | MEDIUM |
| Unified refresh interval | All dashboards use config refresh seconds | Consistent UX | heartbeat config | LOW | LOW |

---

## MEDIUM

| NAME | WHAT | WHY | DATA REQUIRED | COMPLEXITY | USER VALUE |
|------|------|-----|---------------|------------|------------|
| Battery Opportunity Advisor | Read-only recommendations for charge/discharge | Answer "should I use battery?" | price_periods, solar forecast, SOC | MEDIUM | HIGH |
| Pi Phase 2 display fields | Forecast curve, battery today, price min/max on Pi | Complete kiosk | existing backend data | MEDIUM | HIGH |
| Pre-computed daily economics | Collector writes daily financial summary | Fast economy page | readings + prices | MEDIUM | HIGH |
| SSE dashboard push | Replace HTTP polling with snapshot stream | Reduce server load | site_live_snapshots + SSE | MEDIUM | MEDIUM |
| Load disaggregation | House = total - EV - spa estimate | Understand consumption | readings + consumer data | MEDIUM | MEDIUM |
| Forecast learning dashboard | Visualize prediction errors over time | Improve trust/tuning | energy_forecast_snapshots | MEDIUM | MEDIUM |
| Energy control timeline | User-facing automation history | Transparency | energy_control_actions | MEDIUM | MEDIUM |
| CO₂ savings tracker | Estimate avoided emissions from solar | Motivation | solar kWh + emission factor | MEDIUM | LOW |
| Peak demand alerts | Notify when approaching effekttariff | Cost avoidance | peaks API + config | MEDIUM | HIGH |
| Solar forecast snapshot GET | Pre-compute forecast in collector | Fix 34s p95 under load | solar forecast pipeline | MEDIUM | HIGH |

---

## ADVANCED

| NAME | WHAT | WHY | DATA REQUIRED | COMPLEXITY | USER VALUE |
|------|------|-----|---------------|------------|------------|
| Closed-loop forecast tuning | Auto-adjust correction from learning | Better solar accuracy | forecast_learning + correction EMA | HIGH | HIGH |
| Unified horizon optimizer | Single scheduler for EV + spa + battery | True EMS | flexible_load, charging, price_engine | HIGH | HIGH |
| Anomaly detection | Alert on unusual consumption | Fault detection | energy_readings history | HIGH | MEDIUM |
| Away charging finder | Show ChargeFinder stations when vehicle away | Travel utility | ChargeFinder cache + vehicle location | HIGH | MEDIUM |
| Battery arbitrage engine | Automated charge/discharge decisions | Maximize savings | full EnergyState + Heartbeat write | HIGH | HIGH |
| HVAC integration (Sensibo) | Thermostat scheduling by price | Load shifting | **New integration needed** | HIGH | HIGH |
| Multi-site comparison | Compare sites if multiple | Portfolio view | sites + rollups | HIGH | LOW |
| Demand response readiness | Prepare for grid signals | Future-proofing | energy_control + orchestration | HIGH | MEDIUM |

---

## STRATEGIC

| NAME | WHAT | WHY | DATA REQUIRED | COMPLEXITY | USER VALUE |
|------|------|-----|---------------|------------|------------|
| Full EMS platform | Unified EnergyState + optimization + actuation | Market differentiation | All existing + Redis + WS | VERY HIGH | VERY HIGH |
| ML load forecasting | Neural/prophet consumption model | Better optimization | historical readings + weather | VERY HIGH | HIGH |
| Energy marketplace participation | Grid services / frequency response | Revenue stream | battery control + market API | VERY HIGH | HIGH |
| Mobile app parity | iOS/Android full dashboard | User reach | existing API | VERY HIGH | HIGH |
| Multi-tenant SaaS | Host multiple customers securely | Business model | auth + isolation | VERY HIGH | STRATEGIC |
| Digital twin | Simulate what-if scenarios | Planning tool | all models + shadow sim | VERY HIGH | MEDIUM |

---

## Notes

- Items marked "New integration needed" require scope outside current codebase
- Most QUICK WIN and MEDIUM items use **zero new integrations**
- Strategic items assume Heartbeat/inverter write capabilities — **UNKNOWN** extent
