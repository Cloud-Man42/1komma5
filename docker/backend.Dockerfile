FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/energy-core ./packages/energy-core
COPY backend ./backend

RUN uv sync --frozen --package energy-backend --no-dev

FROM python:3.12-slim-bookworm

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY backend ./backend
COPY packages/energy-core ./packages/energy-core
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts/seed.py ./scripts/seed.py
COPY scripts/repair_ev_sessions.py ./scripts/repair_ev_sessions.py
COPY scripts/backfill_financial_daily.py ./scripts/backfill_financial_daily.py
COPY scripts/ensure_timescale_policies.py ./scripts/ensure_timescale_policies.py
COPY scripts/benchmark_solar_forecast.py ./scripts/benchmark_solar_forecast.py

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app

COPY docker/backend-entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
