#!/usr/bin/env bash
# Extract deployment archive to staging, verify integrity, activate into live tree.
# Preserves ~/energy-monitoring/.env and Docker named volumes.
set -euo pipefail

REMOTE_DIR="${1:-energy-monitoring}"
EXPECTED_SHA256="${2:?expected sha256 required}"

ARCHIVE="${HOME}/${REMOTE_DIR}.tar.gz"
STAGING="${HOME}/${REMOTE_DIR}-staging-$$"
LIVE="${HOME}/${REMOTE_DIR}"

cleanup() {
  rm -rf "${STAGING}" 2>/dev/null || true
}
trap cleanup EXIT

if [ ! -f "${ARCHIVE}" ]; then
  echo "Archive missing: ${ARCHIVE}" >&2
  exit 1
fi

echo "${EXPECTED_SHA256}  ${ARCHIVE}" | sha256sum -c -

archive_bytes="$(stat -c%s "${ARCHIVE}")"
avail_kb="$(df -k "${HOME}" | awk 'NR==2 {print $4}')"
need_kb="$((archive_bytes / 1024 * 3))"
if [ "${avail_kb}" -lt "${need_kb}" ]; then
  echo "Insufficient disk space on ${HOME}: need ~${need_kb}KB, have ${avail_kb}KB" >&2
  exit 1
fi

command -v tar >/dev/null
command -v gzip >/dev/null

mkdir -p "${STAGING}"
tar -xzf "${ARCHIVE}" -C "${STAGING}" --no-same-owner --no-same-permissions

for required in backend/app/main.py frontend/package.json packages/energy-core/pyproject.toml docker-compose.yml; do
  if [ ! -e "${STAGING}/${required}" ]; then
    echo "Staging validation failed: missing ${required}" >&2
    exit 1
  fi
done

mkdir -p "${LIVE}"

# Remove root-owned test fixture build dirs left by prior Docker test runs on prod.
if [ -d "${LIVE}/packages/energy-core/tests/fixtures" ]; then
  while IFS= read -r -d '' build_dir; do
    rm -rf "${build_dir}" 2>/dev/null || {
      if [ -f "${HOME}/.emic-deploy-sudo" ]; then
        sudo -S rm -rf "${build_dir}" < "${HOME}/.emic-deploy-sudo"
      else
        echo "Cannot remove stale fixture build dir: ${build_dir}" >&2
        exit 1
      fi
    }
  done < <(find "${LIVE}/packages/energy-core/tests/fixtures" -type d -name '.build' -print0 2>/dev/null || true)
fi

# Replace application code; preserve .env and local runtime state.
remove_tree() {
  local target="$1"
  if [ ! -e "${target}" ]; then
    return 0
  fi
  rm -rf "${target}" 2>/dev/null && return 0
  if [ -f "${HOME}/.emic-deploy-sudo" ]; then
    sudo -S rm -rf "${target}" < "${HOME}/.emic-deploy-sudo"
    return $?
  fi
  echo "Cannot remove ${target} (permission denied and no sudo helper)" >&2
  return 1
}

for item in backend collector frontend packages docker scripts alembic; do
  remove_tree "${LIVE}/${item}"
  cp -a "${STAGING}/${item}" "${LIVE}/${item}"
done
for file in docker-compose.yml Caddyfile pyproject.toml uv.lock alembic.ini .env.production.example; do
  if [ -f "${STAGING}/${file}" ]; then
    cp -a "${STAGING}/${file}" "${LIVE}/${file}"
  fi
done

if [ -f "${HOME}/deploy-linux-remote.sh" ]; then
  cp "${HOME}/deploy-linux-remote.sh" "${LIVE}/deploy-linux-remote.sh"
  chmod +x "${LIVE}/deploy-linux-remote.sh"
fi

echo "Extract and activate OK: ${LIVE}"
