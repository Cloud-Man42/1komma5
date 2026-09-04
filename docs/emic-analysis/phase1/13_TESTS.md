# Phase 1 Tests

New or updated tests covering Phase 1 functionality. Run full suite: [`test-windows.ps1`](../../../test-windows.ps1).

---

## energy-core

| File | Coverage |
|------|----------|
| [`tests/energy/test_unified_state.py`](../../../packages/energy-core/tests/energy/test_unified_state.py) | `UnifiedEnergyState`, all three adapters, W→kW conversion, freshness |
| [`tests/financial/test_aggregation_parity.py`](../../../packages/energy-core/tests/financial/test_aggregation_parity.py) | Daily aggregate vs raw `integrate_financial_stats` parity |
| [`tests/performance/test_instrumentation.py`](../../../packages/energy-core/tests/performance/test_instrumentation.py) | Performance context, middleware `X-Request-Id` |

---

## backend (API)

| File | Coverage |
|------|----------|
| [`tests/test_solar_forecast_snapshot_api.py`](../../../backend/tests/test_solar_forecast_snapshot_api.py) | Snapshot read path, no sync refresh, 404/503 |
| [`tests/test_integration_health_api.py`](../../../backend/tests/test_integration_health_api.py) | Empty providers, 404 unknown site |
| [`tests/test_system_api.py`](../../../backend/tests/test_system_api.py) | Performance endpoint incl. tasks field (existing, extended) |

Related Phase 1 adjacent (pre-existing routes, regression):

| File | Notes |
|------|-------|
| [`tests/test_solar_forecast_api.py`](../../../backend/tests/test_solar_forecast_api.py) | Solar routes |
| [`tests/test_market_prices_api.py`](../../../backend/tests/test_market_prices_api.py) | Price engine |

---

## collector

| File | Coverage |
|------|----------|
| [`tests/test_collector_lanes.py`](../../../collector/tests/test_collector_lanes.py) | `poll_once()` runs fast/medium/slow lanes |

---

## frontend

| File | Coverage |
|------|----------|
| [`src/lib/piDashboardStorage.test.ts`](../../../frontend/src/lib/piDashboardStorage.test.ts) | LKG load/save, connection states, `formatLastUpdated` |

---

## Baseline test status

From [`01_BASELINE.md`](01_BASELINE.md):

| Suite | Result |
|-------|--------|
| pytest | 1110 collected, **PASS** |
| Vitest | 620 tests, **1 fail** (pre-existing `ChargerSetupWizard.test.tsx`) |
| dotnet client | **PASS** |
| `test-windows.ps1` | **FAIL** (blocked by frontend test above) |

Phase 1 additions should not increase failure count beyond the pre-existing wizard test.

---

## Not yet covered (gaps)

- End-to-end collector lane timing under load
- Production re-benchmark automation (manual `scripts/phase1-baseline.ps1`)
- Redis / SSE (design only)
- Auth on `/apple-devices` (deferred)
