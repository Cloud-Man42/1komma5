# EMIC Testing Analysis

---

## 1. Test Inventory

| Suite | Framework | Location | Count |
|-------|-----------|----------|-------|
| energy-core | pytest | `packages/energy-core/tests/` | ~181 test files |
| backend API | pytest + httpx ASGI | `backend/tests/` | ~38 test modules |
| collector | pytest | `collector/tests/` | 2 files |
| frontend | Vitest + RTL | `frontend/src/**/*.test.ts(x)` | ~110 files |
| Windows | dotnet test | `windows/EMIC.Core.Tests/` | UNKNOWN test count |
| Apple | XCTest | `apple/EMICKit/Tests/` | Not in CI |
| **Total pytest collected** | | | **1110 tests** |

**Runner:** `test-windows.ps1` — pytest → dotnet → npm test  
**CI:** `.github/workflows/test.yml` — pytest (non-integration) + npm test

---

## 2. Test Infrastructure

| Feature | Implementation |
|---------|---------------|
| Async tests | pytest-asyncio auto mode |
| API tests | httpx ASGITransport + temp SQLite DB |
| HTTP blocking | Root `conftest.py` blocks outbound HTTP in unit tests |
| Integration marker | `@pytest.mark.integration` for Postgres/network |
| Frontend mocks | fetch mocked in api tests |
| Fixtures | `backend/tests/conftest.py` — app, client, Open-Meteo mock |

---

## 3. Coverage by Domain

| Domain | Backend tests | energy-core tests | Frontend tests | Assessment |
|--------|---------------|-------------------|----------------|------------|
| Economics / financial stats | Partial | Some | `economyDashboardHelpers.test.ts` | **Gap:** full integration |
| Battery calculations | Limited | ledger tests | energy helpers | **Gap** |
| Smart charging | `test_*charging*` | engine tests | ev helpers, reasoning panel | Good |
| Solar forecast | API tests | extensive solar tests | solar dashboard tests | Good |
| Energy totals / integration | readings API | `energy/integration` tests | `energyFlow.test.ts` | Good |
| API parsers | per-integration | chargefinder, mercedes | `api.test.ts`, extended | Good |
| Price engine | `test_price_engine_api` | price_engine tests | prices tests | Good |
| Vehicle freshness | `test_vehicle_freshness_helpers` | vehicle tests | vehicle helpers | Good |
| Display/Pi | display API | — | pi dashboard tests | Moderate |
| Energy control | `test_energy_control_api` | — | EnergyControlPanel | New feature |
| Forecast learning | `test_forecast_learning_api` | — | ForecastLearningCard | Moderate |
| Heartbeat audit | `test_heartbeat_audit_api` | — | HeartbeatAuditPanel | Moderate |
| Security/auth | widget/display auth | device_tokens | — | **Gap:** open API |
| Collector cycle | import test only | — | — | **Gap** |
| Reliability/fallback | resilience tests | providers tests | — | Partial |

---

## 4. Critical Functions — Test Status

| Function | File | Tested? |
|----------|------|---------|
| `list_financial_stats` | `repositories.py` | ⚠️ Partial — complex; dedicated tests UNKNOWN |
| `accumulate_export_interval` | `export_revenue/calculator.py` | ✅ export_revenue tests |
| `normalize_reading` | `normalization/readings.py` | ✅ |
| `integrate_site_energy` | `energy/integration.py` | ✅ |
| Smart charging optimizer | `charging/optimizer.py` | ✅ engine tests |
| EV attribution | `ev_accounting/attribution.py` | ✅ |
| Solar physical model | `solar_forecast/physical.py` | ✅ |
| Price engine refresh | `price_engine/engine.py` | ✅ |
| Snapshot writer | `snapshots/writer.py` | ⚠️ Limited |
| Energy balance engine | `energy_balance/engine.py` | ✅ |
| Vehicle stale guard | `vehicle_repo.py` | ✅ freshness helpers |
| Display overview builder | `display_service.py` | ⚠️ API test only |

---

## 5. Missing Test Categories

| Category | Priority | Notes |
|----------|----------|-------|
| End-to-end economics golden files | HIGH | Known correction for solar-via-battery — needs regression |
| Collector `poll_once` integration | HIGH | Only import test exists |
| Multi-integration failure scenarios | HIGH | Heartbeat down + Mercedes up etc. |
| SSE live-stream | MEDIUM | No test found |
| Performance regression | MEDIUM | `scripts/performance-baseline.ps1` manual |
| Pi offline LKG | MEDIUM | No test |
| Concurrent API load | LOW | solar forecast concurrency issue |
| Apple widget | LOW | Not in CI |

---

## 6. Frontend Test Quality

**Strengths:**
- Co-located tests for every major dashboard
- Helper function tests (economy, ev, solar, vehicle, pi)
- API client tests with mock fetch
- Component render tests with RTL

**Gaps:**
- No Playwright/Cypress E2E
- No visual regression for Pi kiosk
- Polling behavior tested in `useDashboardRefresh.test.ts` but not all hooks

---

## 7. Test Coverage Measurement

| Tool | Status |
|------|--------|
| pytest-cov | Not in CI workflow |
| vitest coverage | `npm run test:coverage` available locally |
| Coverage threshold | Not enforced |

**Coverage percentage: UNKNOWN** — not generated in this analysis.

---

## 8. Recommendations

1. Add golden-file tests for `list_financial_stats` with known reading sequences
2. Collector integration test with mocked Heartbeat provider
3. Add E2E smoke test: dashboard load → verify key metrics present
4. CI: add coverage report artifact
5. Integration test job with Postgres/TimescaleDB in CI
6. Test SSE endpoint behavior
7. Security test: verify credentials not in API responses

---

## 9. Test Commands

```powershell
# Full suite (Windows)
.\test-windows.ps1

# Python only
uv run --all-packages pytest

# Frontend only
cd frontend && npm test

# Integration
make test-integration
```

---

## 10. UNKNOWN

- Exact line coverage percentage
- Flaky test history
- Production smoke test procedures
