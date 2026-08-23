UV ?= uv

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
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

collector-dev:
	$(UV) run --directory collector python -m app

frontend-dev:
	cd frontend && npm run dev

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
