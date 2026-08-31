#!/usr/bin/env bash
# Live colour tuning helper for the Pi kiosk panel (DRM gamma).
# Usage: ./tune-display-color.sh [TEMP_K] [R_G_B]
# Example: ./tune-display-color.sh 4000 1.35_1.08_0.70
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=wayland-env.sh
. "$SCRIPT_DIR/wayland-env.sh"

CARD="${EMIC_KIOSK_DRM_CARD:-0}"
TEMP="${1:-${EMIC_KIOSK_COLOR_TEMP:-4000}}"
RGB="${2:-${EMIC_KIOSK_GAMMA_RGB:-1.35_1.08_0.70}}"
RGB="${RGB//_/:}"
CONFIG=/tmp/emic-gammastep-tune.ini

if ! command -v gammastep >/dev/null 2>&1; then
  echo "gammastep not installed" >&2
  exit 1
fi

CRTC="$("$SCRIPT_DIR/detect-drm-crtc.sh")" || exit 1
"$SCRIPT_DIR/set-broadcast-rgb.sh" || true

cat >"$CONFIG" <<EOF
[general]
gamma=${RGB}
adjustment-method=drm

[drm]
card=${CARD}
crtc=${CRTC}
EOF

echo "Applying ${TEMP}K with channel gamma ${RGB} on drm crtc index ${CRTC}"
echo "Panel OSD should be R=100 G=100 B=100 (Mode USER). Ctrl+C restores when gammastep exits."
gammastep -c "$CONFIG" -m "drm:card=${CARD},crtc=${CRTC}" -P -r -O "$TEMP"
