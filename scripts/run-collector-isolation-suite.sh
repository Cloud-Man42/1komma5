#!/usr/bin/env bash
# Run mandatory Linux isolation security suite with the production collector bwrap 0.8.0 binary (Sprint C.7 / F-RV-02).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTOR_CONTAINER="${EMIC_COLLECTOR_CONTAINER:-energy-monitoring-collector-1}"
HOST_REPO="${EMIC_HOST_REPO:-$ROOT}"
IMAGE_REF="${EMIC_COLLECTOR_IMAGE:-}"
BWRAP_BIN="${EMIC_COLLECTOR_BWRAP_BIN:-/tmp/emic-collector-bwrap-0.8.0}"

echo "=== EMIC Sprint C.7 collector-path isolation suite ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not available" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${COLLECTOR_CONTAINER}"; then
  echo "ERROR: collector container '${COLLECTOR_CONTAINER}' not running" >&2
  exit 1
fi

if [ -z "${IMAGE_REF}" ]; then
  IMAGE_REF="$(docker inspect "${COLLECTOR_CONTAINER}" --format '{{.Config.Image}}@{{.Image}}')"
fi

docker cp "${COLLECTOR_CONTAINER}:/usr/bin/bwrap" "${BWRAP_BIN}"
chmod +x "${BWRAP_BIN}"

BWRAP_VERSION="$("${BWRAP_BIN}" --version 2>/dev/null | head -1 || true)"
BOOTSTRAP_HASH="$(docker exec "${COLLECTOR_CONTAINER}" sha256sum /app/scripts/isolated_runtime_bootstrap.py 2>/dev/null | awk '{print $1}' || true)"
RUNTIME_COMMIT="$(git -C "${HOST_REPO}" rev-parse HEAD 2>/dev/null || echo unknown)"

echo "container: ${COLLECTOR_CONTAINER}"
echo "image: ${IMAGE_REF}"
echo "bwrap: ${BWRAP_VERSION}"
echo "bwrap_path: ${BWRAP_BIN}"
echo "bootstrap_sha256: ${BOOTSTRAP_HASH}"
echo "runtime_commit: ${RUNTIME_COMMIT}"

docker exec "${COLLECTOR_CONTAINER}" test -f /app/scripts/isolated_runtime_bootstrap.py
docker exec "${COLLECTOR_CONTAINER}" /app/.venv/bin/python -c "import energy_core; print(energy_core.__file__)"

export EMIC_BWRAP_PATH="${BWRAP_BIN}"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}"
bash "${ROOT}/scripts/run-linux-isolation-suite.sh"

echo "COLLECTOR-PATH LINUX ISOLATION: PASS"
