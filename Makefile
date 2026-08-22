UV ?= uv
PYTHONPATH := backend:collector:packages/energy-core/src

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
	$(UV) run python -m app --directory collector

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
