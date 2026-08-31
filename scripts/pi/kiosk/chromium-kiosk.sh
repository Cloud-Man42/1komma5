#!/usr/bin/env bash
# Start Chromium in kiosk mode against the local EMIC proxy.
#
# Runs as a native Wayland client under labwc so the page viewport matches the
# panel mode exactly (no Xwayland scaling layer). The proxy injects the device
# token, so no credential ever reaches this script or the browser.
set -euo pipefail

# shellcheck source=wayland-env.sh
. "$(dirname "${BASH_SOURCE[0]}")/wayland-env.sh"

# shellcheck source=kiosk-target.sh
. "$(dirname "${BASH_SOURCE[0]}")/kiosk-target.sh"

KIOSK_URL="$EMIC_KIOSK_URL"
PROFILE_DIR="${EMIC_KIOSK_PROFILE:-/home/hm/.config/emic-kiosk-chromium}"
LOG_FILE="${EMIC_KIOSK_LOG:-/home/hm/.local/share/emic-kiosk/chromium.log}"
HEALTH_URL="$EMIC_KIOSK_HEALTH"

mkdir -p "$(dirname "$LOG_FILE")" "$PROFILE_DIR"

# Belt and braces: these are masked from autostart, but if a session started
# them before the mask was installed they would sit on top of the kiosk.
for stray in squeekboard gnome-keyring-daemon lxpolkit polkit-mate-authentication-agent-1; do
  pkill -x "$stray" 2>/dev/null || true
done

CHROMIUM=""
for candidate in chromium chromium-browser; do
  if command -v "$candidate" >/dev/null 2>&1; then
    CHROMIUM="$candidate"
    break
  fi
done

if [ -z "$CHROMIUM" ]; then
  echo "Chromium not found" >&2
  exit 1
fi

# Chromium refuses to start cleanly after an unclean shutdown unless the crash
# and restore state is cleared, which otherwise surfaces as a "restore pages?"
# bubble on top of the kiosk.
PREFS="$PROFILE_DIR/Default/Preferences"
if [ -f "$PREFS" ]; then
  sed -i 's/"exit_type":"[^"]*"/"exit_type":"Normal"/; s/"exited_cleanly":false/"exited_cleanly":true/' \
    "$PREFS" 2>/dev/null || true
fi

# Restart Chromium if the proxy stays unreachable, so a long EMIC outage cannot
# leave a permanently wedged renderer behind. The page itself already retries.
(
  fails=0
  while true; do
    sleep 60
    if curl -fsS --max-time 10 "$HEALTH_URL" >/dev/null 2>&1; then
      fails=0
    else
      fails=$((fails + 1))
      echo "$(date -Is) health check failed ($fails)" >>"$LOG_FILE"
      if [ "$fails" -ge 5 ]; then
        echo "$(date -Is) restarting chromium after $fails failures" >>"$LOG_FILE"
        pkill -f "user-data-dir=$PROFILE_DIR" || true
        fails=0
      fi
    fi
  done
) &

OZONE_ARGS=()
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
  OZONE_ARGS=(--ozone-platform=wayland --enable-features=UseOzonePlatform)
fi

# labwc does not support wlr-gamma-control. DRM colour correction is optional and
# handled by emic-display-color.service (disabled by default).

exec "$CHROMIUM" \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --hide-crash-restore-bubble \
  --hide-scrollbars \
  --lang=sv \
  --disable-features=Translate,TranslateUI \
  --disable-pinch \
  --disable-component-update \
  --check-for-update-interval=31536000 \
  --password-store=basic \
  --overscroll-history-navigation=0 \
  --autoplay-policy=no-user-gesture-required \
  --force-device-scale-factor=1 \
  --force-color-profile=srgb \
  --user-data-dir="$PROFILE_DIR" \
  "${OZONE_ARGS[@]}" \
  "$KIOSK_URL" >>"$LOG_FILE" 2>&1
