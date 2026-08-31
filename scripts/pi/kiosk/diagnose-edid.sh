#!/usr/bin/env bash
# Identify the panel's native resolution and physical size from EDID.
set -uo pipefail

DRM=/sys/class/drm/card0-HDMI-A-1

echo "=== all modes (preferred first) ==="
cat "$DRM/modes" 2>/dev/null

echo
echo "=== edid decode ==="
if command -v edid-decode >/dev/null 2>&1; then
  edid-decode "$DRM/edid" 2>&1 | head -60
else
  echo "edid-decode not installed"
  echo "edid size: $(stat -c %s "$DRM/edid" 2>/dev/null || echo 0) bytes"
fi

echo
echo "=== physical size reported by compositor ==="
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
wlr-randr 2>&1 | grep -Ei 'physical|mm' || echo "no physical size reported"

echo
echo "=== kernel drm log ==="
dmesg 2>/dev/null | grep -Ei 'hdmi|edid|drm.*mode' | tail -20 || echo "dmesg restricted"

echo
echo "=== boot config overrides ==="
for f in /boot/firmware/config.txt /boot/config.txt; do
  [ -f "$f" ] || continue
  echo "--- $f"
  grep -Ev '^\s*#|^\s*$' "$f"
done

echo
echo "=== cmdline ==="
cat /proc/cmdline
