# EMIC — Energy Monitoring In a Cloud

Energy monitoring dashboard (EMIC) with FastAPI backend, data collector, and Next.js frontend.

## Local Development — No Docker Required

Develop natively on your workstation. Docker is **not** required to run, debug, or test the application.

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 20+
- make (optional; see commands below)

### Setup from a clean clone

```bash
git clone <repository-url>
cd 1komma5

cp .env.development.example .env
cp frontend/.env.local.example frontend/.env.local

make install
make migrate
make seed
```

### Start the application (three terminals)

**Terminal 1 — Backend:**

```bash
make backend-dev
```

**Terminal 2 — Collector:**

```bash
make collector-dev
```

**Terminal 3 — Frontend:**

```bash
make frontend-dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard shows **Demo Home** and **Summer House Denmark** with live mock energy values that change as the collector runs.

### Mock development configuration

```env
APP_ENV=development
HEARTBEAT_PROVIDER=mock
DATABASE_URL=sqlite+aiosqlite:///./energy-dev.db
```

No Docker, PostgreSQL, TimescaleDB, or Heartbeat credentials required.

### SQLite development database

Local development uses a SQLite file (`energy-dev.db` in the project root by default). All readings from the mock collector are persisted there. Delete the file to reset local data.

To use a locally installed PostgreSQL/TimescaleDB instead:

```env
DATABASE_URL=postgresql+asyncpg://energy:password@localhost:5432/energy
ENABLE_TIMESCALEDB=true
make migrate
```

Optionally start only the database via Docker (convenience, not required):

```bash
docker compose -f docker-compose.dev-db.yml up -d
```

### Running tests (no Docker)

```bash
make test
```

On Windows:

```powershell
.\test-windows.ps1
```

**Conventions**

- Backend: pytest + httpx ASGI client with SQLite temp DB (`backend/tests/conftest.py`). Mock Open-Meteo, Heartbeat, and ChargeAmps at provider boundaries.
- Frontend: Vitest + React Testing Library; co-located `*.test.ts(x)`; shared setup in `frontend/src/test/setup.ts`.
- Every change should include at least one happy path and one negative case (422/404/503, empty data, API errors).
- Coverage report (frontend): `cd frontend && npm run test:coverage`

Integration tests (PostgreSQL/TimescaleDB only):

```bash
make test-integration
```

### Windows equivalents (without make)

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv sync
cd frontend; npm ci; cd ..
uv run alembic upgrade head
uv run python scripts/seed.py

# Terminal 1 (from project root)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

# Terminal 2 (from project root)
uv run python -m app --directory collector

# Terminal 3
cd frontend; npm run dev
```

---

## Production Deployment — Docker on Linux DMZ

Production runs entirely in Docker on the Linux DMZ server. No Python, Node.js, or PostgreSQL need to be installed on the host — only Docker Engine and Docker Compose.

### Prerequisites

- Linux server with Docker Engine and Docker Compose plugin

### Deploy

```bash
git clone <repository-url>
cd 1komma5

cp .env.production.example .env
# Edit .env with production secrets (database password, domain, etc.)

docker compose build
docker compose up -d
```

Only **Caddy** publishes ports (80/443) to the host. Backend, frontend, collector, and PostgreSQL are internal.

### Verify TimescaleDB storage

```bash
docker compose exec postgres psql -U energy -d energy -c \
  "SELECT * FROM timescaledb_information.hypertables;"

docker compose exec postgres psql -U energy -d energy -c \
  "SELECT site_id, count(*) FROM energy_readings GROUP BY site_id;"
```

### Production commands

```bash
make docker-build
make docker-up
make docker-down
make docker-logs
make docker-test
```

---

## Architecture

| Component | Local dev | Production |
|-----------|-----------|------------|
| Backend | `uvicorn --reload` on host | FastAPI in Docker |
| Collector | Python process on host | Docker container |
| Frontend | `npm run dev` (hot reload) | Next.js standalone in Docker |
| Database | SQLite (default) or local PostgreSQL | PostgreSQL + TimescaleDB |
| Heartbeat | MockHeartbeatProvider | OneKommaFiveHeartbeatProvider (live-overview) |
| HTTPS | none | Caddy reverse proxy |

Same application code runs in both modes. Differences are configuration only.

---

## Heartbeat integration

Production uses `OneKommaFiveHeartbeatProvider`, which polls `/api/v3/systems/{uuid}/live-overview` for each site with a configured system ID. Bearer tokens are renewed automatically from the stored 1Komma5 account password (~24h JWT).

Configure connection type, credentials, and per-site system UUIDs at `/config` (or via `PUT /api/system/heartbeat-config`).

Local gateway mode is supported when a gateway exposes the same REST API; the Heartbeat hardware box on LAN typically does **not** expose a customer API — use cloud mode instead.
