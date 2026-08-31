#!/usr/bin/env bash
# One-off migration: move the non-secret kiosk display settings out of the
# root-only /etc/emic/kiosk.env (which emic-kiosk.service never loaded) into
# /etc/emic/display.env, which it now does load.
set -euo pipefail

K=/etc/emic/kiosk.env
D=/etc/emic/display.env
RE='^(EMIC_KIOSK_URL|EMIC_KIOSK_HEALTH|EMIC_KIOSK_MODE|EMIC_KIOSK_COLOR_TEMP|EMIC_KIOSK_GAMMA|EMIC_KIOSK_GAMMA_RGB|EMIC_KIOSK_BROADCAST_RGB)='

install -m 644 /tmp/emic-kiosk.service /etc/systemd/system/emic-kiosk.service
install -m 644 /tmp/emic-display-color.service /etc/systemd/system/emic-display-color.service

grep -E "$RE" "$K" >"$D" || true
chown root:root "$D"
chmod 644 "$D"
sed -i -E "/$RE/d" "$K"

systemctl daemon-reload
systemctl restart emic-caddy.service
systemctl restart emic-kiosk.service

echo "--- display.env"
cat "$D"
echo "--- kiosk.env keys"
cut -d= -f1 "$K"
