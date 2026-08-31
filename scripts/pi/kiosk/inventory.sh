#!/usr/bin/env bash
# Read-only inventory of the Pi display stack. Safe to re-run.
echo "=== connectors ==="
for c in /sys/class/drm/card*-*/; do
  name=${c%/}
  name=${name##*/}
  status=$(cat "${c}status" 2>/dev/null)
  echo "${name} = ${status}"
  if [ "$status" = "connected" ]; then
    echo "  modes:"
    head -6 "${c}modes" 2>/dev/null | sed 's/^/    /'
    echo "  enabled: $(cat "${c}enabled" 2>/dev/null)"
  fi
done

echo "=== framebuffer ==="
fbset -s 2>/dev/null || echo "fbset unavailable"

echo "=== session ==="
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-unset}"
loginctl list-sessions --no-legend 2>/dev/null
for s in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
  echo "session ${s}:"
  loginctl show-session "$s" -p Type -p Active -p State -p Name 2>/dev/null | sed 's/^/  /'
done
echo "default target: $(systemctl get-default 2>/dev/null)"

echo "=== compositor / wm ==="
for p in labwc wayfire sway weston Xorg X xinit lightdm gdm3 sddm; do
  if pgrep -x "$p" >/dev/null 2>&1; then echo "running: $p"; fi
done

echo "=== screenshot tools ==="
for t in scrot grim import maim xrandr wlr-randr xwd; do
  printf '%s: ' "$t"
  command -v "$t" 2>/dev/null || echo missing
done

echo "=== chromium ==="
chromium --version 2>/dev/null || chromium-browser --version 2>/dev/null || echo "chromium not found"

echo "=== resources ==="
free -m | head -2
nproc
