#!/usr/bin/env bash
# Capture the live kiosk screen on Wayland/labwc. Writes /tmp/emic-kiosk.png.
set -euo pipefail

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
    case "$sock" in *.lock) continue ;; esac
    [ -S "$sock" ] && WAYLAND_DISPLAY="$(basename "$sock")" && break
  done
fi
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:?no wayland socket found}"

OUT="${1:-/tmp/emic-kiosk.png}"
grim "$OUT"
echo "wrote $OUT"
wlr-randr | grep -E 'current'
file "$OUT"
