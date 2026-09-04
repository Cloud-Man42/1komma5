# TOP 30 Functional Improvements

Based on existing EMIC data, integrations, and partial features.

| # | Category | Improvement | Existing foundation | User value |
|---|----------|-------------|---------------------|------------|
| 1 | QUICK WIN | Integration health overview | readiness + audit + snapshot age | Know system status instantly |
| 2 | QUICK WIN | Best EV charge window card | price_engine today/tomorrow | Save money on charging |
| 3 | QUICK WIN | Economy live refresh | financial-stats API (hook fix) | Accurate costs |
| 4 | QUICK WIN | Global data freshness badge | generated_at in snapshot | Trust in numbers |
| 5 | QUICK WIN | Yesterday vs today comparison | energy_daily rollup | Context |
| 6 | MEDIUM | Battery Opportunity Advisor | price + solar forecast + SOC | Answer battery questions |
| 7 | MEDIUM | Load disaggregation (house/EV/spa) | readings + consumer_samples | Understand consumption |
| 8 | MEDIUM | Pi Phase 2 complete kiosk | display_service extension | Wall display utility |
| 9 | MEDIUM | Forecast learning visualization | energy_forecast_snapshots | Trust + tuning |
| 10 | MEDIUM | Energy control user timeline | energy_control_actions | Automation transparency |
| 11 | MEDIUM | Peak demand / effekttariff alerts | peaks API + site config | Avoid surprise costs |
| 12 | MEDIUM | Battery economics breakdown | battery_energy_ledger | Solar vs grid battery value |
| 13 | MEDIUM | Unified charging history | ev_sessions + vehicle_sessions | Single session view |
| 14 | MEDIUM | Export contract ROI tracker | export_revenue + sell_contract_start | Validate Pulse deal |
| 15 | MEDIUM | CO₂ savings estimate | solar kWh produced | Environmental motivation |
| 16 | MEDIUM | Solar accuracy on main page | solar/accuracy endpoint | Forecast trust |
| 17 | ADVANCED | Closed-loop forecast auto-tune | forecast_learning + correction EMA | Better predictions |
| 18 | ADVANCED | Cross-load optimizer (EV+spa+battery) | flexible_load + charging + price_engine | True smart home |
| 19 | ADVANCED | Anomaly detection alerts | energy_readings patterns | Fault finding |
| 20 | ADVANCED | Away charging with ChargeFinder | vehicle location + station cache | Travel utility |
| 21 | ADVANCED | Seasonal budget forecasting | forecasting.py + actuals | Financial planning |
| 22 | ADVANCED | EMS shadow mode dashboard | collector shadow simulation | Safe experimentation |
| 23 | STRATEGIC | Full battery arbitrage automation | energy_control + Heartbeat write | Maximum savings |
| 24 | STRATEGIC | HVAC price-responsive control | **needs Sensibo/similar** | Largest load shifting |
| 25 | STRATEGIC | ML consumption forecasting | readings + weather history | Better optimization |
| 26 | STRATEGIC | Grid services participation | battery control + market | New revenue |
| 27 | STRATEGIC | Multi-site portfolio dashboard | sites + rollups | Installer/customer view |
| 28 | STRATEGIC | Mobile full-feature app | existing REST API | Accessibility |
| 29 | STRATEGIC | User automation rules (IFTTT-like) | energy_control framework | Customization |
| 30 | STRATEGIC | Energy "score" gamification | savings + forecast accuracy | Engagement |

---

## Priority Tiers for Product Roadmap

### Now (existing data, no new integrations)
#1–6, #9–12, #16

### Next (moderate engineering)
#7–8, #13–15, #17–22

### Future (new capabilities or integrations)
#23–30

---

## Connection to User Questions

| User question | Improvement # |
|---------------|---------------|
| How much producing/using? | #4 freshness, existing dashboards |
| Battery charging? | #6 Battery Advisor |
| Buying/selling grid? | Existing + #4 |
| Is price good? | #2 charge window, existing strategy card |
| Is system optimal? | #1 health strip, #10 control timeline, #6 advisor |
| When to charge car? | #2 (existing engine + better UI) |
| When to heat spa? | Existing spa planner + #18 cross-load |
| When to use battery? | #6, #23 |
