#!/usr/bin/env bash
# Resolves which site and which EMIC server this Pi is pinned to.
#
# Sourced by the kiosk and diagnostic scripts so a Pi in another country reports
# on its own site instead of the Swedish default. The values live in
# /etc/emic/display.env, written by setup-kiosk.sh.

EMIC_DISPLAY_ENV="${EMIC_DISPLAY_ENV:-/etc/emic/display.env}"
if [ -f "$EMIC_DISPLAY_ENV" ]; then
  # shellcheck disable=SC1090
  . "$EMIC_DISPLAY_ENV"
fi

EMIC_SITE_SLUG="${EMIC_SITE_SLUG:-akarp}"
EMIC_SERVER="${EMIC_SERVER:-192.168.50.54}"
EMIC_SERVER_SCHEME="${EMIC_SERVER_SCHEME:-http}"
EMIC_KIOSK_URL="${EMIC_KIOSK_URL:-http://127.0.0.1:8080/display/$EMIC_SITE_SLUG}"
EMIC_KIOSK_HEALTH="${EMIC_KIOSK_HEALTH:-http://127.0.0.1:8080/health}"
