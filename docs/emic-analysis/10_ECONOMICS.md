# EMIC Economics Model

**Primary reference:** `docs/ekonomi-berakning.md`  
**Implementation:** `EnergyReadingRepository.list_financial_stats()` in `packages/energy-core/src/energy_core/db/repositories.py`  
**Export revenue:** `packages/energy-core/src/energy_core/export_revenue/`  
**Frontend display:** `frontend/src/components/economy-dashboard/economyDashboardHelpers.ts`

---

## 1. Price Sources

| Price type | Primary source | Fallback | Storage |
|------------|---------------|----------|---------|
| Spot (EUR) | Heartbeat → `market_prices.spot_price_eur_kwh` | — | Hourly |
| All-in purchase (EUR) | Heartbeat → `market_prices.all_in_price_eur_kwh` | `sites.fallback_purchase_price_sek_kwh` | Hourly |
| Feed-in/export (EUR) | Heartbeat → `market_prices.feed_in_price_eur_kwh` | `sites.export_compensation_sek_kwh` | Hourly |
| 15-min import/export (SEK) | Price engine → `price_periods` | Estimated flag | 15-min |
| EUR→SEK | `EUR_TO_SEK_RATE` (default 11.0) | Config | `market_prices/currency.py` |

**Nord Pool:** Not queried directly — spot comes via Heartbeat API.

**1Komma5 fees:** Embedded in Heartbeat all-in price (network fee, energy tax, markup) when available.

**Site config (economics):**
- `fallback_purchase_price_sek_kwh`
- `export_compensation_sek_kwh`
- `sell_pricing_mode`, `sell_provider`
- `sell_contract_start_date` (Pulse export contract)
- Ore/kWh adjustments, grid benefit rate — via `export_revenue/site_config.py`

---

## 2. Per-Interval Calculation (max 300s gap)

Between consecutive readings:

| Quantity | Formula |
|----------|---------|
| Solar direct to house | `min(solar, max(0, consumption - ev_power - import))` |
| Battery to house | `min(battery_discharge, max(0, consumption - solar_direct))` |
| Grid import/export | Measured `grid_import_w` / `grid_export_w` |
| Interval hours | `(t2 - t1) / 3600`, skip if ≤0 or >300s |

**Purchase price:** Hourly key from `all_in_price_eur_kwh` → SEK, else fallback.

**Export revenue:** Per `export_revenue/calculator.py`:
```
effectiveSellPrice = spotPrice + adjustment − deduction
energySaleRevenue = exportKWh × effectiveSellPrice
gridBenefitRevenue = exportKWh × gridBenefitRate
export_revenue_sek = energySaleRevenue + gridBenefitRevenue
```

Export only counted from `sell_contract_start_date`; pre-contract export → `uncontracted_exported_kwh` (no revenue).

---

## 3. Result Categories

| Metric | Calculation |
|--------|-------------|
| **Solar savings** | solar_direct_kwh × purchase_price |
| **Battery savings** | battery_to_house_kwh × purchase_price |
| **Spot compensation (sold el)** | export_kwh × effectiveSellPrice (time-matched) |
| **Grid benefit (nätnytta)** | export_kwh × gridBenefitRate |
| **Export revenue** | spot compensation + grid benefit (excl. tax credit) |
| **Tax credit (skattereduktion)** | Historical: min(export, import, 30000) × 0.60 SEK/kWh per year; **0 from 2026-01-01** |
| **Grid import cost** | import_kwh × purchase_price |
| **Net cost** | import_cost − export_revenue (no tax credit) |
| **Total economic benefit** | solar + battery + export revenue |
| **Total economic value** | benefit + historical tax credit |

---

## 4. Frontend Mapping (`economyDashboardHelpers.ts`)

| UI label | Backend field / computation |
|----------|----------------------------|
| Net cost | `grid_import_cost_sek − export_revenue_sek` |
| Total savings | solar + battery + sold el (hide empty categories) |
| YTD return | YTD benefit / investment × 100 |
| Cost breakdown (grid/tax/markup) | **Estimated** shares 56/23/15/6% of import cost |
| Payback time | remaining investment / annualized benefit (12 mo) |

---

## 5. EV Economics

**Files:** `ev_accounting/attribution.py`, `session_service.py`, `ev_accounting/coordinator.py`

Per charging session:
- Energy split: `solar_direct_kwh`, `solar_battery_kwh`, `grid_battery_kwh`, `grid_direct_kwh`
- Cost/savings SEK attributed per source
- Vehicle session pricing: migration 054, `vehicles/sessions/`

**Smart charging savings:** `ev_chargers` savings endpoint compares actual vs naive grid charging.

---

## 6. SPA Economics

**Files:** `consumer_accounting/`, `spa_energy/estimate.py`

- Consumer samples → intervals → cost using purchase price at interval time
- `SPA_COST_CALCULATION_ENABLED` config flag

---

## 7. Price Engine (15-min)

**Files:** `price_engine/engine.py`, `strategy.py`, `strategy_service.py`

- Canonical store: `price_periods` (import/export SEK per 15-min)
- Used by: smart charging optimizer, energy strategy card, energy control
- Retention: 90 days
- **Not fully unified** with hourly `market_prices` used by financial stats

---

## 8. Seasonal Year Forecast

**File:** `energy_core/forecasting.py`

- Monthly profiles: `SOLAR_PROFILE`, `BATTERY_PROFILE`, `IMPORT_PROFILE`
- Used by: `GET /api/sites/{slug}/forecast` (year forecast)
- **Not** live spot-based — shape templates, not ML

---

## 9. Known Issues / Risks

| Issue | Severity | Detail |
|-------|----------|--------|
| Dual price granularity | MEDIUM | Financial stats use hourly `market_prices`; smart charging uses 15-min `price_periods` |
| Python-side integration | HIGH | Performance — all readings loaded for period |
| Cost breakdown percentages | LOW | Frontend estimates 56/23/15/6 — not from actual tariff components |
| VAT (moms) | UNKNOWN | Not explicitly modeled in `list_financial_stats` |
| Battery grid-charge cost | MEDIUM | Ledger tracks grid energy cost separately; may not appear in house savings |
| Pre-contract export | LOW | Correctly excluded from revenue but may confuse users |
| Tax credit phase-out 2026 | OK | Implemented in `tax_credit.py` |

---

## 10. Double-Counting Prevention

**Fixed (2026):** Solar→battery→house path no longer credited twice (see `docs/ekonomi-berakning.md`).

**Identity:** `solar_self + battery_self + imported == consumption` per day.

**Energy balance:** Separate check for measurement double-counting (Sungrow vs Heartbeat vs Halo).

---

## 11. Missing Cost/Revenue Items

| Item | Status |
|------|--------|
| Fixed monthly fees | Not modeled |
| Capacity tariffs (effekttariff) | Peaks API exists (`/peaks`) but not in financial stats |
| VAT on export revenue | UNKNOWN |
| Battery degradation cost | Not modeled |
| EV session public charging (ChargeFinder) | Not in home economics |
| SPA as separate line | Partial via spa economics endpoint |

---

## 12. Recommendations

1. Unify on `price_periods` for all economics calculations
2. Pre-aggregate daily financial stats in collector
3. Expose effekttariff/peak cost in economy dashboard
4. Document VAT handling explicitly (or add moms field)
5. Align price engine strategy display with financial stats numbers
