#!/usr/bin/env bash
# Keep the panel lit 24/7 on Raspberry Pi OS with labwc (Wayland).
#
# `xset -dpms` does not apply here: the session is Wayland, so X11 DPMS/
# screensaver settings are either rejected ("server does not have extension for
# -dpms option") or apply only to Xwayland clients. On wlroots compositors
# blanking is driven by an idle daemon, so the work is:
#
#   1. stop any idle daemon (swayidle/xscreensaver/light-locker)
#   2. force the output on via wlr-output-power-management (wlopm)
#   3. disable kernel console blanking on the VTs behind the compositor
#
# System suspend/hibernate is handled separately by masking the sleep targets
# and by logind IdleAction=ignore (see setup-kiosk.sh).
set -uo pipefail

# shellcheck source=wayland-env.sh
. "$(dirname "${BASH_SOURCE[0]}")/wayland-env.sh"

for daemon in swayidle xscreensaver light-locker xss-lock; do
  pkill -x "$daemon" 2>/dev/null && echo "stopped $daemon"
done

if [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wlopm >/dev/null 2>&1; then
  wlopm --on '*' >/dev/null 2>&1 && echo "wlopm: all outputs on"
else
  echo "wlopm unavailable or no wayland socket; skipping output power-on" >&2
fi

# Kernel console blanking still applies to the VT the compositor runs on.
if command -v setterm >/dev/null 2>&1; then
  for tty in /dev/tty1 /dev/console; do
    [ -w "$tty" ] || continue
    setterm --blank 0 --powerdown 0 --powersave off >"$tty" 2>/dev/null || true
  done
fi

if [ -w /sys/module/kernel/parameters/consoleblank ]; then
  echo 0 >/sys/module/kernel/parameters/consoleblank 2>/dev/null || true
fi
