#!/usr/bin/env bash
# Read-only diagnostics for the EMIC Pi kiosk: display stack, services, proxy, resources.
set -uo pipefail

section() { printf '\n=== %s ===\n' "$1"; }

# shellcheck source=kiosk-target.sh
. "$(dirname "${BASH_SOURCE[0]}")/kiosk-target.sh"

section "session"
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-unset}"
loginctl list-sessions --no-legend 2>/dev/null || true
for s in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
  echo "session $s:"
  loginctl show-session "$s" -p Type -p Active -p State -p Name 2>/dev/null
done

section "compositor"
ps -eo comm= | grep -Ei 'labwc|wayfire|sway|Xorg|Xwayland|lightdm|greetd' | sort -u || echo "none matched"

section "tools"
for t in grim wlr-randr wlopm swayidle swaymsg xset chromium; do
  printf '%s: ' "$t"
  command -v "$t" || echo missing
done

section "display modes"
for f in /sys/class/drm/card*/status; do
  [ -f "$f" ] || continue
  st=$(cat "$f")
  [ "$st" = "connected" ] || continue
  d=$(dirname "$f")
  echo "$(basename "$d"): $st"
  head -3 "$d/modes" 2>/dev/null
done

section "services"
systemctl is-enabled emic-caddy emic-kiosk 2>&1
systemctl is-active emic-caddy emic-kiosk 2>&1

section "sleep targets"
systemctl is-enabled sleep.target suspend.target hibernate.target hybrid-sleep.target 2>&1

section "logind idle config"
grep -Ev '^\s*#|^\s*$' /etc/systemd/logind.conf /etc/systemd/logind.conf.d/*.conf 2>/dev/null || echo "defaults only"

section "console blanking"
cat /sys/module/kernel/parameters/consoleblank 2>/dev/null || echo "n/a"
grep -o 'consoleblank=[0-9]*' /proc/cmdline || echo "consoleblank not on cmdline"

section "proxy ($EMIC_SITE_SLUG via $EMIC_SERVER_SCHEME://$EMIC_SERVER)"
curl -s -o /dev/null -w 'display page: %{http_code}\n' "$EMIC_KIOSK_URL"
curl -s -o /tmp/emic-ov.json -w 'api: %{http_code} %{size_download} bytes\n' \
  "http://127.0.0.1:8080/api/v1/display/overview/$EMIC_SITE_SLUG"

section "resources"
uptime
free -m
echo "chromium processes: $(pgrep -c chromium || echo 0)"
ps -eo pmem,pcpu,comm --sort=-pmem | head -8
