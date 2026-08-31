#!/usr/bin/env bash
# Force the panel to its native mode before Chromium starts.
#
# kanshi already applies this at session start; this is the safety net for the
# case where the kiosk unit restarts after kanshi has exited, and it waits for
# the compositor so a cold boot does not race the session.
set -uo pipefail

# shellcheck source=wayland-env.sh
. "$(dirname "${BASH_SOURCE[0]}")/wayland-env.sh"

OUTPUT="${EMIC_KIOSK_OUTPUT:-HDMI-A-1}"
MODE="${EMIC_KIOSK_MODE:-1024x600}"

for _ in $(seq 1 30); do
  [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break
  sleep 1
  . "$(dirname "${BASH_SOURCE[0]}")/wayland-env.sh"
done

if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  echo "no wayland socket; leaving display mode unchanged" >&2
  exit 0
fi

current="$(wlr-randr 2>/dev/null | awk '/\(current\)/{print $1; exit}')"
if [ "$current" = "$MODE" ]; then
  echo "output $OUTPUT already at $MODE"
else
  echo "switching $OUTPUT from ${current:-unknown} to $MODE"
  wlr-randr --output "$OUTPUT" --mode "$MODE" || echo "wlr-randr mode set failed" >&2
fi

# Panels without EDID can come back powered down after a mode switch.
command -v wlopm >/dev/null 2>&1 && wlopm --on "$OUTPUT" >/dev/null 2>&1 || true
