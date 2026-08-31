#!/usr/bin/env bash
# Post-reboot verification for the EMIC kiosk.
# Checks boot time, services, display mode, Chromium state, proxy, blanking and resources.
set -uo pipefail

section() { printf '\n=== %s ===\n' "$1"; }

# shellcheck source=kiosk-target.sh
. "$(dirname "${BASH_SOURCE[0]}")/kiosk-target.sh"

section "boot"
echo "booted at: $(uptime -s)"
uptime
systemd-analyze 2>/dev/null | head -2 || true

section "services"
for unit in emic-caddy emic-display-color emic-kiosk; do
  printf '%-14s enabled=%s active=%s\n' "$unit" \
    "$(systemctl is-enabled "$unit" 2>&1)" "$(systemctl is-active "$unit" 2>&1)"
done
systemctl show emic-kiosk -p NRestarts --value | sed 's/^/emic-kiosk restarts: /'

section "compositor + display mode"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
ps -eo comm= | grep -Ei 'labwc|kanshi' | sort -u
wlr-randr 2>/dev/null | grep -E '\(current\)|Enabled' || echo "wlr-randr unavailable"
wlopm 2>/dev/null || true
if pgrep -x gammastep >/dev/null; then
  echo "gammastep: running (colour temp from /etc/emic/kiosk.env EMIC_KIOSK_COLOR_TEMP)"
else
  echo "gammastep: not running"
fi

section "chromium"
echo "processes: $(pgrep -c chromium || echo 0)"
# Confirm kiosk mode and that no X11 fallback is in use.
tr '\0' ' ' </proc/"$(pgrep -f 'ozone-platform' | head -1)"/cmdline 2>/dev/null |
  tr ' ' '\n' | grep -E '^--(kiosk|ozone-platform|lang|force-device-scale-factor)' || true

section "blanking / sleep"
systemctl is-enabled sleep.target suspend.target hibernate.target hybrid-sleep.target 2>&1
grep -h '' /etc/systemd/logind.conf.d/*.conf 2>/dev/null | grep -Ev '^#|^$' || echo "no logind drop-in"
echo "consoleblank: $(cat /sys/module/kernel/parameters/consoleblank 2>/dev/null || echo n/a)"
grep -o 'consoleblank=[0-9]*' /proc/cmdline || echo "consoleblank not on cmdline"
echo "idle daemons: $(pgrep -x swayidle >/dev/null && echo swayidle || echo none)"
loginctl show-session "$(loginctl list-sessions --no-legend | awk '$5=="wayland"||$3=="hm"{print $1; exit}')" \
  -p IdleHint -p IdleSinceHint 2>/dev/null || true

section "proxy + api ($EMIC_SITE_SLUG via $EMIC_SERVER_SCHEME://$EMIC_SERVER)"
curl -s -o /dev/null -w 'health:  %{http_code}\n' "$EMIC_KIOSK_HEALTH"
curl -s -o /dev/null -w 'page:    %{http_code} %{size_download} bytes\n' "$EMIC_KIOSK_URL"
curl -s -o /tmp/emic-ov.json -w 'api:     %{http_code} %{size_download} bytes\n' \
  "http://127.0.0.1:8080/api/v1/display/overview/$EMIC_SITE_SLUG"
# The token must never be reachable without the proxy injecting it.
curl -s -o /dev/null -w 'direct api without token: %{http_code}\n' \
  "$EMIC_SERVER_SCHEME://$EMIC_SERVER/api/v1/display/overview/$EMIC_SITE_SLUG"

section "resources"
free -m
top -bn1 | head -5
echo "chromium rss total: $(ps -eo rss,comm | awk '/chromium/{s+=$1} END{printf "%.0f MiB\n", s/1024}')"

section "chromium log (errors only, last 15)"
grep -aiE 'error|fail' ~/.local/share/emic-kiosk/chromium.log 2>/dev/null | tail -15 || echo "no log"
