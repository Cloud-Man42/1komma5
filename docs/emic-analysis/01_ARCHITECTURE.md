# EMIC Architecture Overview

**Project:** EMIC — Energy Monitoring In a Cloud  
**Repository:** `1komma5`  
**Analysis date:** 2026-09-03  
**Migration head:** `057_energy_control_interface`  
**Source:** Code-based discovery only

---

## 1. Purpose

EMIC is a home energy monitoring and partial energy management platform. It ingests site energy data (primarily via 1Komma5 Heartbeat), stores time-series readings, computes economics and forecasts, controls EV charging (Charge Amps), integrates vehicles (Mercedes), spa (Arctic Spa), and exposes dashboards via Next.js web UI, Raspberry Pi kiosk, Apple widgets, and Windows tray.

---

## 2. Programming Languages & Runtimes

| Component | Language | Runtime Version | Source |
|-----------|----------|-----------------|--------|
| Backend API | Python | 3.12+ | `backend/pyproject.toml`, `docker/backend.Dockerfile` |
| Domain library | Python | 3.12+ | `packages/energy-core/pyproject.toml` |
| Collector | Python | 3.12+ | `collector/pyproject.toml` |
| Frontend | TypeScript | Node 20+ (CI: 22) | `frontend/package.json`, `.github/workflows/test.yml` |
| Apple app | Swift 5.10 | iOS 17+ | `apple/project.yml` |
| Windows widget | C# | .NET 8 | `windows/EMIC.Core/` |
| Migrations | Python/Alembic | — | `alembic/` |
| Package manager | uv | workspace | `pyproject.toml`, `uv.lock` |

---

## 3. Frameworks & Libraries

### Backend
- **FastAPI** ≥0.115 — HTTP API (`backend/app/main.py`)
- **Uvicorn** — ASGI server
- **SQLAlchemy 2** async — ORM (`packages/energy-core/src/energy_core/db/`)
- **Pydantic Settings** — configuration (`energy_core/config.py`)
- **Alembic** — schema migrations
- **httpx** — external HTTP
- **onekommafive** ≥0.1.46 — Heartbeat SDK
- **scikit-learn, numpy** — solar intelligence ML
- **websockets, protobuf** — Mercedes vehicle transport

### Frontend
- **Next.js 15** App Router — `frontend/src/app/`
- **React 19**
- **Recharts** — charts
- **Vitest + React Testing Library** — tests

### Infrastructure
- **Docker Compose** — 5 services
- **Caddy 2** — reverse proxy, TLS
- **TimescaleDB** (PostgreSQL 16) — production database

---

## 4. System Components

### 4.1 Docker Stack (`docker-compose.yml`)

| Service | Image/Build | Port | Role |
|---------|-------------|------|------|
| `caddy` | `caddy:2-alpine` | 80, 443 (published) | TLS, routes `/api/*` → backend:8000, else → frontend:3000 |
| `frontend` | `docker/frontend.Dockerfile` | 3000 (internal) | Next.js standalone |
| `backend` | `docker/backend.Dockerfile` | 8000 (internal) | FastAPI REST API |
| `collector` | `docker/collector.Dockerfile` | none | Background poll loop |
| `postgres` | `timescale/timescaledb:latest-pg16` | 5432 (internal) | Primary datastore |

**Volumes:** `postgres_data`, `caddy_data`, `caddy_config`, `emic_secrets` (Fernet key)

**Backend entrypoint** (`docker/backend-entrypoint.sh`): ensures secret key, runs Alembic migrations, seeds DB, starts uvicorn.

### 4.2 Non-Docker Clients

| Client | Path | Protocol |
|--------|------|----------|
| Browser dashboard | Next.js frontend | HTTPS → Caddy |
| Raspberry Pi kiosk | `scripts/pi/kiosk/` | Local Caddy :8080 → remote EMIC |
| Apple iOS + widgets | `apple/` | `/api/v1/widget/*` with device token |
| Windows tray | `windows/EMIC.Tray/` | Widget API |

---

## 5. Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENTS: Browser, Pi Kiosk, Apple Widget, Windows Tray     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────┐
│  REVERSE PROXY: Caddy (TLS, gzip, X-Forwarded-*)            │
└──────────────┬─────────────────────────────┬──────────────────┘
               │                             │
┌──────────────▼──────────┐    ┌─────────────▼─────────────────┐
│  FRONTEND (Next.js 15)  │    │  BACKEND (FastAPI)            │
│  - App Router pages     │    │  - 24 API routers (~158 EP)   │
│  - api.ts fetch layer   │    │  - widget/display auth only   │
│  - React hooks/state    │    │  - thin orchestration         │
└──────────────┬──────────┘    └─────────────┬─────────────────┘
               │                             │
               └──────────────┬──────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  DOMAIN LAYER: packages/energy-core                         │
│  - db/models, repositories (31 repos)                       │
│  - integrations, charging, solar, vehicles, spa, prices   │
│  - energy_state, snapshots, aggregation, forecast_learning  │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐  ┌──────────▼─────────┐  ┌───────▼──────────┐
│  COLLECTOR    │  │  DATABASE          │  │  EXTERNAL APIs   │
│  poll loop    │  │  SQLite (dev)      │  │  Heartbeat, CA,  │
│  ~30-60s      │  │  PG+Timescale(prod)│  │  Mercedes, Spa,  │
│  enrichment   │  │  ~60 tables        │  │  SMHI/DMI/Meteo  │
└───────────────┘  └────────────────────┘  └──────────────────┘
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Frontend** | `frontend/src/` | UI, polling, local state, display formatting |
| **API layer** | `backend/app/api/*.py` | HTTP routing, Pydantic schemas, auth gates |
| **Backend services** | `backend/app/widget_service.py`, `display_service.py` | Widget/display aggregation + cache |
| **Domain / service** | `packages/energy-core/src/energy_core/` | Business logic, integrations, calculations |
| **Integration layer** | `energy_core/integrations/`, `providers/`, `heartbeat/`, `vehicles/` | External API clients, resilience |
| **Data layer** | `energy_core/db/` | ORM models, repositories, session factory |
| **Collector** | `collector/app/collector.py` | Ingestion, enrichment, control loops |
| **Cache** | `energy_core/cache/service.py`, snapshot tables | L1 in-process + DB snapshots |

---

## 6. API Surface

- **158 REST endpoints** across 24 router modules
- Global: `GET /health`
- Most routes: `/api/*`
- Exceptions: `/semp/*` (no `/api` prefix), widget `/api/v1/widget/*`, display `/api/v1/display/*`
- **No WebSocket endpoints** in FastAPI; Mercedes WebSocket runs in collector only
- **SSE:** `GET /api/sites/{slug}/live-stream`, `/api/kiosk/{slug}/stream`

Full endpoint inventory in `EMIC_ANALYSIS.json` → `api_endpoints`.

---

## 7. Database

| Environment | Engine | Connection |
|-------------|--------|------------|
| Development | SQLite | `sqlite+aiosqlite:///./energy-dev.db` |
| Production | PostgreSQL 16 + TimescaleDB | `postgresql+asyncpg://...@postgres:5432/energy` |
| Tests | SQLite temp files | `backend/tests/conftest.py` |

**~60 SQLAlchemy models** in `packages/energy-core/src/energy_core/db/models.py`  
**57 Alembic migrations** in `alembic/versions/`  
**TimescaleDB:** optional via `ENABLE_TIMESCALEDB=true`; hypertables on `energy_readings`, `consumer_samples`, `vehicle_state_history`; continuous aggregates `energy_readings_5min`, `energy_readings_1hour`

---

## 8. Cache & Snapshots

| Mechanism | TTL | Location |
|-----------|-----|----------|
| InMemoryCacheService (L1) | configurable + jitter | `energy_core/cache/service.py` |
| site_live_snapshots | per collector cycle | `energy_core/snapshots/writer.py` |
| Widget snapshot cache | 15s default | `WIDGET_SNAPSHOT_CACHE_SECONDS` |
| Display overview cache | 3s | `backend/app/display_service.py` |
| Display weather cache | 60s | `display_service.py` |
| LastKnownGoodStore | per-key max_age | `providers/resilience.py` |
| Solar weather DB cache | 45 min | `SOLAR_WEATHER_CACHE_MINUTES` |
| ChargeFinder lookup cache | 7 days | `CHARGEFINDER_CACHE_TTL_SECONDS` |

**No Redis, no distributed cache** — process-local only (known limitation per `docs/performance/REPORT.md`).

---

## 9. Background Workers

**No Celery, APScheduler, or cron in backend.**

All background work in **collector process** (`collector/app/collector.py`):
- Main asyncio poll loop (interval from DB `heartbeat_settings.poll_interval_seconds`, default 30–60s)
- `VehicleIntegrationSupervisor` — per-site asyncio tasks
- `SolarForecastCoordinator` — refresh every `SOLAR_FORECAST_REFRESH_MINUTES` (default 30)
- `ArcticSpaPollingService` — 60s / 15s during cleaning

---

## 10. Authentication & Authorization

| Surface | Auth | File |
|---------|------|------|
| Most `/api/*` | **None** (open) | Assumes trusted LAN |
| Widget API | Bearer token, scope `widget.read`, rate limit 60/min | `backend/app/widget_auth.py` |
| Display API | Bearer or `emic_display_token` cookie, scope `display.read` | `backend/app/display_auth.py` |
| Apple device admin | **None** | `backend/app/api/apple_devices.py` |
| Heartbeat | JWT via email/password → encrypted in DB | `heartbeat_auth.py`, `secrets.py` |
| Charge Amps | API key + credentials (env or per-charger) | `chargers/charge_amps.py` |
| Mercedes | OAuth login, tokens encrypted in DB | `vehicles/mercedes/auth/` |
| Arctic Spa | X-API-KEY per site | `integrations/arctic_spa/client.py` |

**Secrets at rest:** Fernet `SecretBox` via `EMIC_SECRET_KEY` or `./emic-secret.key` (`energy_core/secrets.py`); Docker volume `/var/lib/emic`.

---

## 11. Logging & Monitoring

| Component | Location | Behavior |
|-----------|----------|----------|
| Request performance | `energy_core/performance/middleware.py` | Logs `perf requestId=... totalMs dbMs externalMs`; adds `X-Request-Id` |
| SQL tracking | `energy_core/performance/sql_tracking.py` | Counts queries; logs slow queries ≥100ms |
| Performance store | `energy_core/performance/store.py` | In-memory metrics at `GET /api/system/performance` |
| Widget metrics | `backend/app/widget_auth.py` | Structured `widget_api` log lines |
| Log level | `LOG_LEVEL` env | `energy_core/config.py` |

**Gaps:** No structured correlation IDs across collector+backend; no integration health dashboard; no Prometheus/export metrics.

---

## 12. Testing

| Suite | Framework | Count | Path |
|-------|-----------|-------|------|
| Python | pytest | ~1110 collected | `packages/energy-core/tests/`, `backend/tests/`, `collector/tests/` |
| Frontend | Vitest | ~110 test files | `frontend/src/**/*.test.ts(x)` |
| Windows | dotnet test | UNKNOWN count | `windows/EMIC.Core.Tests/` |
| Apple | XCTest | Not in CI | `apple/EMICKit/Tests/` |
| Runner | `test-windows.ps1` | Sequential: pytest → dotnet → npm test | repo root |
| CI | GitHub Actions | pytest (non-integration) + npm test | `.github/workflows/test.yml` |

Integration tests marked `@pytest.mark.integration`; repo `conftest.py` blocks outbound HTTP in unit tests.

---

## 13. CI/CD & Deployment

- **CI:** `.github/workflows/test.yml` — push/PR to main/master
- **Deploy:** Manual via `scripts/deploy-linux.ps1`, `scripts/deploy-linux-remote.sh`
- **No deploy/release CI workflows** in repository
- **Makefile:** `docker-build`, `docker-up`, `migrate`, `seed`, `test`

---

## 14. Configuration

Central settings: `packages/energy-core/src/energy_core/config.py` (`Settings` class, reads `.env`)

Templates:
- `.env.example`, `.env.development.example`, `.env.production.example`
- `frontend/.env.local.example`

Production runtime config also via `/config` UI → `PUT /api/system/heartbeat-config` (DB-stored).

Key env vars documented in `06_INTEGRATIONS.md` and `05_CACHE.md`.

---

## 15. Real-time Communication

| Mechanism | Where | Interval |
|-----------|-------|----------|
| SSE snapshot stream | `backend/app/api/snapshot.py` | Polls DB every 1s, emits on change |
| Frontend HTTP polling | Various hooks | 4s (Pi) to 300s |
| Collector poll | `collector/app/collector.py` | 30–60s |
| Mercedes WebSocket | collector supervisor | Adaptive (ping 30s) |
| No SignalR, no FastAPI WebSocket | — | — |

---

## 16. Text Architecture Diagram

```
External APIs / Devices
  ├── 1Komma5 Heartbeat (energy, prices, EV aggregate, Sungrow proxy)
  ├── Charge Amps (EV charger control)
  ├── Mercedes Cloud (vehicle telemetry, commands)
  ├── Arctic Spa API (spa status, control)
  ├── SMHI / DMI / Open-Meteo (weather, radiation)
  └── ChargeFinder web (away charging lookup)
         │
         ▼
    COLLECTOR (asyncio loop, 30-60s)
      ├── Ingest readings → energy_readings
      ├── Price engine refresh → price_periods
      ├── Live overview prefetch (1× per site per cycle)
      ├── EV/consumer/vehicle accounting
      ├── Solar forecast + evaluation
      ├── Forecast learning sync
      ├── Energy control sync
      ├── Hourly/daily rollups
      ├── Snapshot writer → site_live_snapshots
      ├── Smart charging engine → Charge Amps
      └── Virtual Heartbeat bridge + EMS shadow
         │
         ▼
    PostgreSQL + TimescaleDB (~60 tables)
         │
         ▼
    BACKEND FastAPI (158 endpoints)
      ├── Dashboard/snapshot (DB-only GET, no live Heartbeat)
      ├── Widget/display (cached, auth-gated)
      └── Admin/config (open)
         │
         ▼
    FRONTEND Next.js 15
      ├── Site dashboards (/sites/[slug]/*)
      ├── Pi kiosk (/display/[slug]/*)
      └── Config/admin (/config, /admin/*)
         │
         ▼
    Clients: Browser, Pi Chromium, Apple Widget, Windows Tray
```

---

## 17. UNKNOWN Items

- Production host sizing (CPU/RAM) — not in repo
- Exact production traffic/concurrent users — measured once in performance baseline (2026-08-28)
- Redis/multi-worker deployment timeline — deferred per performance report
- eBEcon integration — not found in codebase
- Apple test coverage in CI — not wired
