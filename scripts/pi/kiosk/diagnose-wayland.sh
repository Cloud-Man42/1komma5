#!/usr/bin/env bash
# Wayland/labwc specifics: active output mode, idle daemons, DPMS state.
set -uo pipefail

section() { printf '\n=== %s ===\n' "$1"; }

# The kiosk unit exports these; reuse them so wlr-randr/grim can reach the compositor.
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
    case "$sock" in *.lock) continue ;; esac
    [ -S "$sock" ] && export WAYLAND_DISPLAY="$(basename "$sock")" && break
  done
fi
echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-unset}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}"

section "active output mode"
wlr-randr 2>&1 || echo "wlr-randr failed"

section "power state"
wlopm 2>&1 || echo "wlopm failed"

section "idle daemons"
ps -eo pid,comm= | grep -Ei 'swayidle|idle|xss|light-locker|xscreensaver' | grep -v grep || echo "none running"

section "labwc config"
for f in ~/.config/labwc/autostart ~/.config/labwc/rc.xml /etc/xdg/labwc/autostart; do
  echo "--- $f"
  [ -f "$f" ] && cat "$f" || echo "(missing)"
done

section "wayfire/desktop autostart"
ls -1 ~/.config/autostart /etc/xdg/autostart 2>/dev/null | sort -u || true

section "screen off timeout (raspi desktop)"
grep -rIn --include='*.ini' --include='*.conf' -e 'idle' -e 'blank' -e 'dpms' \
  ~/.config/wf-panel-pi.ini ~/.config/labwc ~/.config/wayfire.ini 2>/dev/null || echo "no idle settings found"
