#!/usr/bin/env bash
# Run mandatory Linux isolation security suite (Sprint C.6).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && [ -z "${EMIC_LINUX_SUITE_NO_SUDO:-}" ]; then
  exec sudo -E env "PATH=${PATH}" bash "$0" "$@"
fi

# Ensure dedicated runtime identity exists when launching bwrap as root.
if [ "$(id -u)" -eq 0 ]; then
  groupadd -g 10001 emic-module 2>/dev/null || true
  useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin emic-module 2>/dev/null || true
fi

cd "$ROOT"

BWRAP_BIN="${EMIC_BWRAP_PATH:-$(command -v bwrap)}"
if [ -z "${BWRAP_BIN}" ] || [ ! -x "${BWRAP_BIN}" ]; then
  echo "ERROR: bubblewrap (bwrap) not found" >&2
  exit 1
fi

echo "bwrap: ${BWRAP_BIN}"
"${BWRAP_BIN}" --version | head -1

VENV="${ROOT}/.venv-linux-isolation"
if [ ! -x "${VENV}/bin/python" ]; then
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install -q --upgrade pip
  "${VENV}/bin/pip" install -q pytest pytest-asyncio httpx pydantic-settings sqlalchemy aiosqlite alembic packaging
  "${VENV}/bin/pip" install -q -e "${ROOT}/packages/energy-core" -e "${ROOT}/backend"
fi

export APP_ENV=test
export PYTHONPATH="${ROOT}/packages/energy-core/tests:${PYTHONPATH:-}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///${ROOT}/.tmp/linux-isolation.db}"
export ISOLATED_RUNTIME_ENABLED=true
export THIRD_PARTY_RUNTIME_ENABLED=true
export ISOLATED_RUNTIME_SANDBOX=bwrap
export ISOLATED_RUNTIME_SOCKET_DIR="${ROOT}/.tmp/runtime-sockets"
export ISOLATED_RUNTIME_DATA_ROOT="${ROOT}/.tmp/runtime-data"
export EMIC_MODULES_PATH="${ROOT}/.tmp/modules"
export EMIC_ALLOW_UNSIGNED_MODULES=true
mkdir -p "${ROOT}/.tmp/runtime-sockets" "${ROOT}/.tmp/runtime-data" "${ROOT}/.tmp/modules"

echo "Rebuilding sandbox-demo fixture package..."
(cd packages/energy-core && "${VENV}/bin/python" tests/fixtures/modules/integration.sandbox-demo/build_emicpkg.py)
(cd packages/energy-core && "${VENV}/bin/python" tests/fixtures/modules/integration.pre-drop-probe/build_emicpkg.py)
(cd packages/energy-core && "${VENV}/bin/python" tests/fixtures/modules/integration.runtime-e2e/build_emicpkg.py)
if [ ! -f packages/energy-core/tests/fixtures/modules/integration.sensibo-1.0.0.emicpkg ]; then
  echo "Building integration.sensibo fixture..."
  (cd modules/sensibo && "${VENV}/bin/python" build_emicpkg.py)
  cp -f modules/sensibo/integration.sensibo-1.0.0.emicpkg packages/energy-core/tests/fixtures/modules/
  "${VENV}/bin/python" scripts/sign_sensibo_package.py 2>/dev/null || true
fi

echo "Refreshing editable energy-core install for isolation tests..."
"${VENV}/bin/pip" install -q -e "${ROOT}/packages/energy-core" -e "${ROOT}/backend"

echo "Running Sprint E Sensibo Linux E2E (mandatory, zero skips)..."
set +e
"${VENV}/bin/python" -m pytest \
  packages/energy-core/tests/platform/isolation/test_linux_sensibo_e2e.py \
  -v --tb=short \
  --junitxml="${ROOT}/.tmp/linux-sensibo-junit.xml" \
  2>&1 | tee "${ROOT}/.tmp/linux-sensibo.log"
sensibo_rc=${PIPESTATUS[0]}
sensibo_passed=$(grep -Eo '[0-9]+ passed' "${ROOT}/.tmp/linux-sensibo.log" | tail -1 || true)
sensibo_failed=$(grep -Eo '[0-9]+ failed' "${ROOT}/.tmp/linux-sensibo.log" | tail -1 || true)
sensibo_skipped=$(grep -Eo '[0-9]+ skipped' "${ROOT}/.tmp/linux-sensibo.log" | tail -1 || true)
echo "SENSIBO E2E SUMMARY: ${sensibo_passed:-0 passed}, ${sensibo_failed:-0 failed}, ${sensibo_skipped:-0 skipped}"
if [ "$sensibo_rc" -ne 0 ]; then
  exit "$sensibo_rc"
fi
if [ -n "${sensibo_skipped:-}" ] && [ "${sensibo_skipped%% *}" != "0" ]; then
  echo "ERROR: mandatory Sensibo E2E tests were skipped" >&2
  exit 2
fi

echo "Running Linux isolation integration suite..."
set +e
"${VENV}/bin/python" -m pytest \
  packages/energy-core/tests/platform/isolation/ \
  -v --tb=short \
  -m integration \
  --junitxml="${ROOT}/.tmp/linux-isolation-junit.xml" \
  2>&1 | tee "${ROOT}/.tmp/linux-isolation.log"
rc=${PIPESTATUS[0]}
set -e

passed=$(grep -Eo '[0-9]+ passed' "${ROOT}/.tmp/linux-isolation.log" | tail -1 || true)
failed=$(grep -Eo '[0-9]+ failed' "${ROOT}/.tmp/linux-isolation.log" | tail -1 || true)
skipped=$(grep -Eo '[0-9]+ skipped' "${ROOT}/.tmp/linux-isolation.log" | tail -1 || true)

echo ""
echo "LINUX ISOLATION SUMMARY: ${passed:-0 passed}, ${failed:-0 failed}, ${skipped:-0 skipped}"

if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
if [ -n "${skipped:-}" ] && [ "${skipped%% *}" != "0" ]; then
  echo "ERROR: mandatory Linux tests were skipped" >&2
  exit 2
fi
exit 0
