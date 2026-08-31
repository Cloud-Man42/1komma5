#!/usr/bin/env bash
# Force full RGB range on the HDMI connector (cheap panels often default to limited).
set -euo pipefail

CARD="${EMIC_KIOSK_DRM_CARD:-0}"
CONNECTOR="${EMIC_KIOSK_DRM_CONNECTOR:-35}"
MODE="${EMIC_KIOSK_BROADCAST_RGB:-Full}"
MODetest_BIN="${MODETEST_BIN:-modetest}"

if ! command -v "$MODetest_BIN" >/dev/null 2>&1; then
  echo "modetest not installed" >&2
  exit 0
fi

case "$MODE" in
  Full|1) value=1 ;;
  Limited|2) value=2 ;;
  Auto|0|*) value=0 ;;
esac

if "$MODetest_BIN" -M vc4 -w "${CONNECTOR}:Broadcast RGB:${value}" 2>/dev/null; then
  echo "Broadcast RGB=${MODE} on connector ${CONNECTOR}"
else
  echo "Broadcast RGB not set (connector ${CONNECTOR})" >&2
fi
