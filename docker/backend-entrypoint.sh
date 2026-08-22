#!/bin/sh
set -e
cd /app
alembic upgrade head
cd /app
python scripts/seed.py
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8000