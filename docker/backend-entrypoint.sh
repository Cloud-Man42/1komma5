#!/bin/sh
set -e

ensure_secret_key() {
  secret_dir="/var/lib/emic"
  secret_file="${EMIC_SECRET_KEY_PATH:-$secret_dir/secret.key}"
  mkdir -p "$(dirname "$secret_file")"

  if [ -f "$secret_file" ]; then
    return 0
  fi

  for legacy in /app/backend/emic-secret.key /app/emic-secret.key /app/collector/emic-secret.key; do
    if [ -f "$legacy" ]; then
      cp "$legacy" "$secret_file"
      echo "Migrated EMIC secret key to $secret_file"
      return 0
    fi
  done

  python - <<'PY'
from cryptography.fernet import Fernet
from pathlib import Path
import os

path = Path(os.environ.get("EMIC_SECRET_KEY_PATH", "/var/lib/emic/secret.key"))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(Fernet.generate_key().decode("ascii"), encoding="utf-8")
print(f"Generated EMIC secret key at {path}")
PY
}

ensure_secret_key

cd /app
alembic upgrade head
cd /app
python scripts/seed.py
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
