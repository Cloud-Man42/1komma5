# Financial Daily Aggregation

**Status:** Implemented (flag-gated, off by default)  
**Migration:** `059_financial_daily`

---

## Problem

`GET /api/sites/{slug}/financial-stats` scans full `energy_readings` + `market_prices` on every request. Baseline p95 **~3089 ms** at 1 user, **~28 s** at 10 users ([`01_BASELINE.md`](01_BASELINE.md)). Target: **p95 < 300 ms** via pre-aggregated daily rows.

---

## Table: `financial_daily`

Composite PK: `(site_id, day)`.

| Column group | Fields |
|--------------|--------|
| Energy (kWh) | `solar_self_kwh`, `battery_self_kwh`, `export_kwh`, `import_kwh` |
| Savings/cost (SEK) | `solar_savings_sek`, `battery_savings_sek`, `grid_import_cost_sek` |
| Pricing metadata | `market_priced_kwh`, `priced_denominator_kwh`, `spot_priced_kwh`, `fallback_priced_kwh`, `negative_price_kwh` |
| Export revenue | `energy_sale_sek`, `grid_benefit_sek`, `contracted_export_kwh`, `uncontracted_export_kwh` |

**Files:** [`alembic/versions/059_financial_daily.py`](../../../alembic/versions/059_financial_daily.py), [`financial/daily_repo.py`](../../../packages/energy-core/src/energy_core/financial/daily_repo.py).

---

## Shared logic: `aggregation.py`

**File:** [`packages/energy-core/src/energy_core/financial/aggregation.py`](../../../packages/energy-core/src/energy_core/financial/aggregation.py)

| Function | Role |
|----------|------|
| `build_price_maps()` | Hour-keyed purchase/spot/feed-in EUR maps from `market_prices` |
| `integrate_financial_daily_accumulators()` | Interval integration over readings → per-day `FinancialDailyAccumulator` |
| `aggregate_daily_to_period_stats()` | Roll daily rows up to day/month/year `FinancialStatResult` |
| `integrate_financial_stats()` | Legacy full-scan path (same math, no aggregates) |

Both API and collector use the same integration code — parity enforced by tests.

---

## Write path (collector slow lane)

`FinancialAggregationService.rollup_site()` ([`financial/service.py`](../../../packages/energy-core/src/energy_core/financial/service.py)):

- Default window: last **2 days** per cycle.
- Reads readings + prices for window, integrates to daily accumulators, upserts `financial_daily`.

Slow lane task name: `financial_rollup:{site.slug}` — see [`05_COLLECTOR_LANES.md`](05_COLLECTOR_LANES.md).

**Backfill:** [`scripts/backfill_financial_daily.py`](../../../scripts/backfill_financial_daily.py) — `--site akarp --days 365`.

---

## Read path (API)

**Route:** `GET /api/sites/{slug}/financial-stats` — [`backend/app/api/readings.py`](../../../backend/app/api/readings.py)

`EnergyReadingRepository.list_financial_stats(..., use_aggregates=settings.financial_aggregates_enabled)`:

- When flag **on** and daily rows exist → `aggregate_daily_to_period_stats()` (fast).
- When flag **off** or no rows → full `integrate_financial_stats()` scan (baseline behaviour).

---

## Flag: `FINANCIAL_AGGREGATES_ENABLED`

| Default | `false` |
|---------|---------|
| Env | `FINANCIAL_AGGREGATES_ENABLED=true` to enable read path |

**Rollout:** Run migration → backfill → enable flag → re-benchmark. Without backfill, API falls back to full scan even with flag on.

---

## Parity tests

[`packages/energy-core/tests/financial/test_aggregation_parity.py`](../../../packages/energy-core/tests/financial/test_aggregation_parity.py):

- Same synthetic readings/prices through daily integration + period rollup vs direct `integrate_financial_stats()`.
- Asserts kWh and SEK fields match within tolerance.

---

## Performance expectation

| Path | Expected p95 (1 user) |
|------|----------------------|
| Full scan (flag off) | ~3000 ms (baseline) |
| Aggregates (flag on, backfilled) | < 300 ms (pending deploy measurement — [`14_RESULTS.md`](14_RESULTS.md)) |
