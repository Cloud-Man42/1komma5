#!/usr/bin/env bash
# Capture page-level console output for the kiosk route.
#
# Runs a short-lived headless Chromium against the same proxied URL as the kiosk
# and reports CONSOLE messages the page emitted. Chromium's own stderr noise
# (GPU/DBus/GCM) is filtered out so only page errors remain.
set -uo pipefail

# shellcheck source=kiosk-target.sh
. "$(dirname "${BASH_SOURCE[0]}")/kiosk-target.sh"

URL="${1:-$EMIC_KIOSK_URL}"
PROFILE="$(mktemp -d)"
LOG="$(mktemp)"

trap 'rm -rf "$PROFILE" "$LOG"' EXIT

chromium \
  --headless=new \
  --no-sandbox \
  --disable-gpu \
  --window-size=1024,600 \
  --user-data-dir="$PROFILE" \
  --enable-logging=stderr \
  --log-level=0 \
  --virtual-time-budget=20000 \
  --dump-dom "$URL" >/dev/null 2>"$LOG"

echo "=== page console messages ==="
if grep -aE 'CONSOLE|Uncaught|Unhandled' "$LOG" | grep -avE 'DEPRECATED_ENDPOINT'; then
  :
else
  echo "(none)"
fi

echo
echo "=== failed subresource requests ==="
grep -aE 'net::ERR|Failed to load resource' "$LOG" || echo "(none)"

echo
echo "=== chromium stderr categories (counts) ==="
grep -aoE 'ERROR:[a-z_/.]+' "$LOG" | sort | uniq -c | sort -rn | head -10 || echo "(none)"
