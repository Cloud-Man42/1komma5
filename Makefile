UV ?= uv

# Host ports the dev targets bind (GH-46). Each default is the value that
# target bound before it became configurable, so a developer who sets nothing
# sees no change; set the variable in the environment or on the command line
# (`make backend-dev BACKEND_PORT=9001`) to move the port.
#
# `$(or $(strip ...),<default>)` rather than `?=`: GNU Make counts an exported
# but empty `BACKEND_PORT=` as already set, so `?=` would leave it empty and
# hand uvicorn a bare `--port` with no value. This form falls back for the
# empty case as well as the unset one, matching the `${VAR:-default}` semantics
# the compose files use for HTTP_PORT/HTTPS_PORT/POSTGRES_PORT.
BACKEND_PORT := $(or $(strip $(BACKEND_PORT)),8000)
# 3000 is `next dev`'s own default; FRONTEND_PORT reaches it through PORT,
# which its `-p, --port` option reads (`next dev --help`).
FRONTEND_PORT := $(or $(strip $(FRONTEND_PORT)),3000)

# Module resolution for the workspace packages (energy_core, app.main, app.collector)
# comes from the editable installs that `make install` (`uv sync --all-packages`) writes
# into .venv as .pth files -- not from PYTHONPATH. Do not re-add a PYTHONPATH assignment
# here: GNU Make forwards a variable into a recipe's subshell only if it came from the
# environment, was set on the command line, or was marked `export`, so a plain assignment
# silently does nothing while looking like it configures every recipe (GH-12).

.PHONY: install migrate seed backend-dev collector-dev frontend-dev lint test test-integration docker-build docker-up docker-down docker-logs docker-test

install:
	$(UV) sync --all-packages
	cd frontend && npm ci

migrate:
	$(UV) run alembic upgrade head

seed:
	$(UV) run python scripts/seed.py

backend-dev:
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) --app-dir backend

collector-dev:
	$(UV) run --directory collector python -m app

frontend-dev:
	cd frontend && PORT=$(FRONTEND_PORT) npm run dev

test:
	$(UV) run pytest
	cd frontend && npm test

test-integration:
	$(UV) run pytest -m integration

# The Python lint gate (GH-28). Both commands are read-only: `ruff format
# --check` reports what `ruff format` would rewrite without rewriting it.
# Make aborts the target on the first recipe line that exits nonzero and
# propagates that status, so `make lint` exits nonzero whenever either
# command does -- do not prefix either line with `-`, and do not append
# `|| true`, or the gate stops reporting failures it has found.
#
# Python only, on purpose. The frontend has its own gate (`npm run lint`,
# GH-23); folding it in here would make this target's exit code depend on
# eslint as well as ruff, which is not what its name promises.
lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-test:
	docker compose up -d --wait
	curl -sf http://localhost/health || curl -sf http://localhost:8000/health
	docker compose down
