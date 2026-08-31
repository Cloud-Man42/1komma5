#!/usr/bin/env bash
# Apply fixed colour correction via DRM gamma (labwc does not support wlr-gamma-control).
set -euo pipefail

# shellcheck source=wayland-env.sh
. "$(dirname "${BASH_SOURCE[0]}")/wayland-env.sh"

CARD="${EMIC_KIOSK_DRM_CARD:-0}"
TEMP="${EMIC_KIOSK_COLOR_TEMP:-4000}"
GAMMA_RGB="${EMIC_KIOSK_GAMMA_RGB:-1.35_1.08_0.70}"
GAMMA_RGB="${GAMMA_RGB//_/:}"
CONFIG="${EMIC_KIOSK_GAMMA_CONFIG:-${XDG_RUNTIME_DIR:-/run/user/1000}/emic-gammastep.ini}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for _ in $(seq 1 60); do
  [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break
  sleep 1
  # shellcheck source=wayland-env.sh
  . "$SCRIPT_DIR/wayland-env.sh"
done

if ! command -v gammastep >/dev/null 2>&1; then
  echo "gammastep not installed" >&2
  exit 1
fi

if ! command -v modetest >/dev/null 2>&1; then
  echo "modetest not installed" >&2
  exit 1
fi

CRTC="$("$SCRIPT_DIR/detect-drm-crtc.sh")" || exit 1

"$SCRIPT_DIR/set-broadcast-rgb.sh" || true

umask 022
cat >"$CONFIG" <<EOF
[general]
gamma=${GAMMA_RGB}
adjustment-method=drm

[drm]
card=${CARD}
crtc=${CRTC}
EOF

echo "display colour: ${TEMP}K rgb=${GAMMA_RGB} drm card=${CARD} crtc=${CRTC}"
gammastep -c "$CONFIG" -m "drm:card=${CARD},crtc=${CRTC}" -P -r -O "$TEMP"
