# EMIC Code Quality

---

## 1. Repository Structure

| Area | Files (approx) | Assessment |
|------|------------------|------------|
| `packages/energy-core` | 433 Python files | Large domain monolith — cohesive but heavy |
| `backend/app` | ~30 files | Appropriately thin API layer |
| `frontend/src` | ~110 test files + components | Well-tested UI |
| `collector` | 3 app files | Focused |

---

## 2. Large Files (Refactoring Candidates)

| File | Role | Concern |
|------|------|---------|
| `energy_core/db/repositories.py` | Energy readings, financial stats, peaks, history | **Very large** — multiple responsibilities |
| `energy_core/db/models.py` | All ORM models (~1500 lines) | Large but acceptable for ORM |
| `frontend/src/lib/api.ts` | All fetch functions (~78 exports) | **Large** — could split by domain |
| `backend/app/schemas.py` | All Pydantic models | Large — mirror of API surface |
| `backend/app/api/spa.py` | Spa routes | Many endpoints in one file |
| `backend/app/api/vehicles.py` | Vehicle routes | Many endpoints |
| `backend/app/api/solar_forecast.py` | Solar routes + logic | Mixed routing and business logic |
| `backend/app/api/dashboard.py` | Dashboard assembly | Complex computation in API layer |
| `collector/app/collector.py` | Full poll orchestration | Long but readable |

---

## 3. Dead Code & Legacy

| Item | Status |
|------|--------|
| Modbus integration | Removed (migration 012); catalog references remain as "future" |
| `energy_devices` table | Dropped |
| `market_prices` hourly store | Legacy — parallel to `price_periods` |
| `solar_forecast_model_profiles` | v1 alongside v2 intelligence |
| `nobil_integration_status` | May be superseded by ChargeFinder |
| SEMP protocol | Active but niche (`/semp/*`) |
| Mock providers | Intentional for dev/test |

---

## 4. TODO / FIXME

**Application code:** Almost no TODO/FIXME in hand-written Python/TS (grep found only protobuf-generated files).

**Implication:** Either well-maintained or missing debt markers.

---

## 5. Duplicate Code

| Duplication | Locations |
|-------------|-----------|
| Dashboard computation | `dashboard.py` + `display_service.py` + `snapshots/writer.py` + `energy_state/service.py` |
| Section navigation | Consolidated via `hashSectionNavigation.ts` (health report Fase 4) |
| Chart time helpers | Consolidated in `chartTime.ts` |
| Energy integration | Consolidated in `energy/integration.py` |
| Price EUR→SEK | Centralized in `market_prices/currency.py` |
| Polling hooks | Similar pattern in 6+ `use*DashboardData.ts` files |

---

## 6. Coupling

| Coupling | Detail |
|----------|--------|
| Backend → energy-core | Clean — all business logic delegated |
| Frontend → api.ts | All domains through single file — tight |
| Dashboard → many repos | `dashboard.py` imports widely from energy-core |
| Collector → everything | Collector imports 20+ coordinators — expected for orchestrator |
| display_service → dashboard helpers | `_compute_ev`, `_compute_price` imported from dashboard.py — **cross-layer coupling** |

---

## 7. Cohesion

**Strong cohesion:**
- `ev_accounting/`, `vehicles/mercedes/`, `solar_intelligence/`, `price_engine/` — well-bounded domains

**Weak cohesion:**
- `repositories.py` — readings, prices, financial stats, peaks in one class
- `schemas.py` — entire API surface in one module

---

## 8. Circular Dependencies

No explicit circular import failures reported in tests. Potential risk:
- `display_service.py` imports from `dashboard.py`
- `dashboard.py` may indirectly reference display schemas

**Status:** UNKNOWN — tests pass (1110 pytest collected).

---

## 9. Naming & Conventions

- Consistent Python package structure under `energy_core/`
- Frontend: co-located tests (`*.test.ts(x)`)
- Swedish UI labels, English code — consistent pattern
- API routes: RESTful `/sites/{slug}/...`

---

## 10. Refactoring Candidates (Priority)

| Priority | Target | Action |
|----------|--------|--------|
| 1 | `repositories.py` | Split into ReadingRepo, FinancialRepo, PeakRepo |
| 2 | `api.ts` | Split into domain modules (evApi, solarApi, etc.) |
| 3 | Dashboard assembly | Single `DashboardBuilder` service in energy-core |
| 4 | `display_service` ↔ `dashboard` | Shared builder, remove cross-import |
| 5 | `use*DashboardData` hooks | Generic `useSiteEndpoint` with config |
| 6 | `schemas.py` | Split by router domain |
| 7 | Legacy `market_prices` | Migrate all consumers to `price_periods` then deprecate |

---

## 11. Code Quality Strengths

- Comprehensive test suite (~1110 pytest + ~110 frontend tests)
- Typed Python (dataclasses, Pydantic, SQLAlchemy 2 typed mappings)
- Typed TypeScript frontend
- Performance middleware and SQL tracking
- Resilience patterns (circuit breaker, LKG)
- Health report documents prior consolidation work
- Cursor rules enforce testing on changes

---

## 12. UNKNOWN

- Static analysis (ruff/mypy) CI enforcement — ruff configured but no CI job
- Frontend ESLint strictness
- Code coverage percentage — not measured in CI
