UV ?= uv

# Module resolution for the workspace packages (energy_core, app.main, app.collector)
# comes from the editable installs that `make install` (`uv sync --all-packages`) writes
# into .venv as .pth files -- not from PYTHONPATH. Do not re-add a PYTHONPATH assignment
# here: GNU Make forwards a variable into a recipe's subshell only if it came from the
# environment, was set on the command line, or was marked `export`, so a plain assignment
# silently does nothing while looking like it configures every recipe (GH-12).

.PHONY: install migrate seed backend-dev collector-dev frontend-dev test test-integration docker-build docker-up docker-down docker-logs docker-test

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
