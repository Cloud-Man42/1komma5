FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/energy-core ./packages/energy-core
COPY collector ./collector
COPY scripts/verify_mercedes_eqe_commands.py ./scripts/verify_mercedes_eqe_commands.py

RUN uv sync --frozen --package energy-collector --no-dev

FROM python:3.12-slim-bookworm

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY collector ./collector
COPY packages/energy-core ./packages/energy-core
COPY scripts/verify_mercedes_eqe_commands.py ./scripts/verify_mercedes_eqe_commands.py
COPY scripts/isolated_runtime_bootstrap.py ./scripts/isolated_runtime_bootstrap.py

RUN apt-get update && apt-get install -y --no-install-recommends bubblewrap \
    && rm -rf /var/lib/apt/lists/* \
    && (groupadd -g 10001 emic-module || true) \
    && (useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin emic-module || true)

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/collector

CMD ["python", "-m", "app"]
