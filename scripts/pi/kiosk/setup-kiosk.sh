#!/usr/bin/env bash
# Interactive setup for EMIC Raspberry Pi kiosk.
# Does NOT store passwords in repo. Prompts for device token once.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIOSK_USER="${EMIC_KIOSK_USER:-hm}"
KIOSK_HOME="$(getent passwd "$KIOSK_USER" | cut -d: -f6)"
KIOSK_HOME="${KIOSK_HOME:-/home/$KIOSK_USER}"
INSTALL_DIR="${EMIC_KIOSK_HOME:-$KIOSK_HOME/emic-kiosk}"
# Split on purpose: ENV_FILE holds the bearer token and is root-only, loaded by
# emic-caddy.service alone. DISPLAY_ENV_FILE holds the non-secret display
# settings and is what emic-kiosk.service reads, so the token never reaches
# Chromium's environment.
ENV_FILE="/etc/emic/kiosk.env"
DISPLAY_ENV_FILE="/etc/emic/display.env"
CADDY_FILE="/etc/emic/Caddyfile"
DISPLAY_KEYS='EMIC_KIOSK_URL|EMIC_KIOSK_HEALTH|EMIC_KIOSK_MODE|EMIC_KIOSK_COLOR_TEMP|EMIC_KIOSK_GAMMA|EMIC_KIOSK_GAMMA_RGB|EMIC_KIOSK_BROADCAST_RGB|EMIC_SITE_SLUG|EMIC_SERVER|EMIC_SERVER_SCHEME|EMIC_SERVER_HOST'

# Which house this Pi shows, and which EMIC server it talks to. Both are
# parameters so a Pi at another site needs no edit to any file:
#   EMIC_SITE_SLUG=summer-house-denmark EMIC_SERVER=emic.example.com \
#     EMIC_SERVER_SCHEME=https sudo -E bash setup-kiosk.sh
SITE_SLUG="${EMIC_SITE_SLUG:-akarp}"
SERVER="${EMIC_SERVER:-emic.inacloud.se}"
SERVER_SCHEME="${EMIC_SERVER_SCHEME:-https}"
SERVER_HOST="${EMIC_SERVER_HOST:-$SERVER}"

# Re-running the installer must not clobber a hand-tuned URL, so the target is
# only rewritten when the operator passed it in explicitly.
RETARGET=0
if [ -n "${EMIC_SITE_SLUG:-}" ] || [ -n "${EMIC_SERVER:-}" ] || [ -n "${EMIC_SERVER_SCHEME:-}" ] || [ -n "${EMIC_SERVER_HOST:-}" ]; then
  RETARGET=1
fi

# Upserts a key in an env file, so re-runs stay idempotent.
set_env_key() {
  local file="$1" key="$2" value="$3"
  sed -i "/^${key}=/d" "$file"
  printf '%s=%s\n' "$key" "$value" >>"$file"
}

echo "=== EMIC Pi Kiosk Setup ==="
echo "Site:   $SITE_SLUG"
echo "Server: $SERVER_SCHEME://$SERVER"
echo "This script configures local Caddy proxy + Chromium kiosk for /display/$SITE_SLUG"
echo

if [ "$(id -u)" -ne 0 ]; then
  echo "Re-run with sudo for systemd and /etc/emic installation."
  exit 1
fi

echo "--- System inventory ---"
uname -a
cat /etc/os-release
hostnamectl || true
systemctl get-default || true
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-unset}"
ps -eo comm= | grep -Ei 'labwc|wayfire|sway|Xorg' | sort -u || true
command -v chromium || command -v chromium-browser || echo "Chromium: not found"
chromium --version 2>/dev/null || chromium-browser --version 2>/dev/null || true
for f in /sys/class/drm/card*/modes; do
  [ -f "$f" ] && echo "$f:" && head -3 "$f"
done

mkdir -p /etc/emic "$INSTALL_DIR"
install -m 644 "$SCRIPT_DIR/wayland-env.sh" "$INSTALL_DIR/wayland-env.sh"
install -m 755 "$SCRIPT_DIR/disable-blanking.sh" "$INSTALL_DIR/disable-blanking.sh"
install -m 755 "$SCRIPT_DIR/set-display-mode.sh" "$INSTALL_DIR/set-display-mode.sh"
install -m 755 "$SCRIPT_DIR/detect-drm-crtc.sh" "$INSTALL_DIR/detect-drm-crtc.sh"
install -m 755 "$SCRIPT_DIR/set-broadcast-rgb.sh" "$INSTALL_DIR/set-broadcast-rgb.sh"
install -m 755 "$SCRIPT_DIR/start-display-color.sh" "$INSTALL_DIR/start-display-color.sh"
install -m 755 "$SCRIPT_DIR/tune-display-color.sh" "$INSTALL_DIR/tune-display-color.sh"
install -m 755 "$SCRIPT_DIR/chromium-kiosk.sh" "$INSTALL_DIR/chromium-kiosk.sh"
install -m 755 "$SCRIPT_DIR/screenshot.sh" "$INSTALL_DIR/screenshot.sh"
install -m 755 "$SCRIPT_DIR/verify-boot.sh" "$INSTALL_DIR/verify-boot.sh"
install -m 755 "$SCRIPT_DIR/disable-desktop-dialogs.sh" "$INSTALL_DIR/disable-desktop-dialogs.sh"
install -m 644 "$SCRIPT_DIR/kiosk-target.sh" "$INSTALL_DIR/kiosk-target.sh"
install -m 644 "$SCRIPT_DIR/colortest.html" "$INSTALL_DIR/colortest.html"
install -m 644 "$SCRIPT_DIR/Caddyfile" "$CADDY_FILE"

# Enterprise policy suppresses the translate bubble and other browser UI that
# would otherwise draw on top of the dashboard.
install -d -m 755 /etc/chromium/policies/managed
install -m 644 "$SCRIPT_DIR/chromium-policy.json" /etc/chromium/policies/managed/emic-kiosk.json

# kanshi is launched by /etc/xdg/labwc/autostart; this profile pins the panel to
# its native mode, which wlroots otherwise gets wrong because the panel has no EDID.
install -d -o "$KIOSK_USER" -g "$KIOSK_USER" -m 755 "$KIOSK_HOME/.config/kanshi"
install -o "$KIOSK_USER" -g "$KIOSK_USER" -m 644 \
  "$SCRIPT_DIR/kanshi-config" "$KIOSK_HOME/.config/kanshi/config"

# Nothing may draw over the kiosk: mask the keyring prompt, on-screen keyboard
# and polkit agents for this user.
runuser -u "$KIOSK_USER" -- "$INSTALL_DIR/disable-desktop-dialogs.sh" || \
  echo "Warning: could not mask desktop autostart entries" >&2

if [ ! -f "$ENV_FILE" ]; then
  read -rsp "Paste EMIC device token (display.read, hidden): " TOKEN
  echo
  umask 077
  printf 'EMIC_KIOSK_TOKEN=%s\n' "$TOKEN" >"$ENV_FILE"
  chown root:root "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Wrote $ENV_FILE"
else
  echo "$ENV_FILE already exists — leaving token unchanged"
fi

# Upgrade path: display settings used to live in the root-only kiosk.env, where
# emic-kiosk.service (which does not load it) silently ignored them. Move them.
if [ ! -f "$DISPLAY_ENV_FILE" ]; then
  cat >"$DISPLAY_ENV_FILE" <<EOF
EMIC_SITE_SLUG=$SITE_SLUG
EMIC_SERVER=$SERVER
EMIC_SERVER_SCHEME=$SERVER_SCHEME
EMIC_SERVER_HOST=$SERVER_HOST
EMIC_KIOSK_URL=http://127.0.0.1:8080/display/$SITE_SLUG
EMIC_KIOSK_HEALTH=http://127.0.0.1:8080/health
EMIC_KIOSK_COLOR_TEMP=4000
EMIC_KIOSK_GAMMA=1.0
EMIC_KIOSK_GAMMA_RGB=1.35_1.08_0.70
EMIC_KIOSK_BROADCAST_RGB=Full
EOF
  # Carry over any values the operator had already tuned in kiosk.env.
  if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line; do
      key="${line%%=*}"
      sed -i "/^${key}=/d" "$DISPLAY_ENV_FILE"
      printf '%s\n' "$line" >>"$DISPLAY_ENV_FILE"
    done < <(grep -E "^(${DISPLAY_KEYS})=" "$ENV_FILE" 2>/dev/null || true)
  fi
  echo "Wrote $DISPLAY_ENV_FILE"
elif [ "$RETARGET" -eq 1 ]; then
  set_env_key "$DISPLAY_ENV_FILE" EMIC_SITE_SLUG "$SITE_SLUG"
  set_env_key "$DISPLAY_ENV_FILE" EMIC_SERVER "$SERVER"
  set_env_key "$DISPLAY_ENV_FILE" EMIC_SERVER_SCHEME "$SERVER_SCHEME"
  set_env_key "$DISPLAY_ENV_FILE" EMIC_SERVER_HOST "$SERVER_HOST"
  set_env_key "$DISPLAY_ENV_FILE" EMIC_KIOSK_URL "http://127.0.0.1:8080/display/$SITE_SLUG"
  echo "Re-pointed $DISPLAY_ENV_FILE at $SITE_SLUG on $SERVER_SCHEME://$SERVER"
fi
chown root:root "$DISPLAY_ENV_FILE"
chmod 644 "$DISPLAY_ENV_FILE"

# One source of truth: strip the migrated keys so kiosk.env holds only the token.
sed -i -E "/^(${DISPLAY_KEYS})=/d" "$ENV_FILE"

MISSING=()
command -v caddy >/dev/null 2>&1 || MISSING+=(caddy)
command -v curl >/dev/null 2>&1 || MISSING+=(curl)
# Wayland tooling: mode pinning, output power, screenshots for verification.
command -v wlr-randr >/dev/null 2>&1 || MISSING+=(wlr-randr)
command -v wlopm >/dev/null 2>&1 || MISSING+=(wlopm)
command -v grim >/dev/null 2>&1 || MISSING+=(grim)
command -v kanshi >/dev/null 2>&1 || MISSING+=(kanshi)
command -v gammastep >/dev/null 2>&1 || MISSING+=(gammastep)
command -v modetest >/dev/null 2>&1 || MISSING+=(libdrm-tests)

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "Installing: ${MISSING[*]}"
  apt-get update
  apt-get install -y "${MISSING[@]}"
fi

# apt's caddy package enables a system-wide service on admin port 2019 — disable it.
systemctl disable --now caddy.service 2>/dev/null || true

install -m 644 "$SCRIPT_DIR/emic-caddy.service" /etc/systemd/system/emic-caddy.service
install -m 644 "$SCRIPT_DIR/emic-display-color.service" /etc/systemd/system/emic-display-color.service
install -m 644 "$SCRIPT_DIR/emic-kiosk.service" /etc/systemd/system/emic-kiosk.service

systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target 2>/dev/null || true

# logind must never act on idle or the lid/power key for a wall display.
mkdir -p /etc/systemd/logind.conf.d
cat >/etc/systemd/logind.conf.d/99-emic-kiosk.conf <<'EOF'
# EMIC wall display: never idle-act, never suspend.
[Login]
IdleAction=ignore
IdleActionSec=0
HandleSuspendKey=ignore
HandleHibernateKey=ignore
HandleLidSwitch=ignore
EOF
# Reloading is enough; restarting logind would tear down the graphical session.
systemctl reload systemd-logind 2>/dev/null || true

# Kernel console blanking on the VT behind the compositor.
if [ -f /boot/firmware/cmdline.txt ] && ! grep -q 'consoleblank=0' /boot/firmware/cmdline.txt; then
  sed -i '1 s/$/ consoleblank=0/' /boot/firmware/cmdline.txt
  echo "Added consoleblank=0 to /boot/firmware/cmdline.txt (applies next boot)"
fi

systemctl daemon-reload
systemctl enable emic-caddy.service emic-kiosk.service
systemctl restart emic-caddy.service
systemctl restart emic-kiosk.service || echo "Start emic-kiosk manually after graphical login if needed"
# emic-display-color is installed but left disabled: the panel reproduces colour
# correctly on its own, so enable it only to set a warmer white point by choice.
systemctl disable emic-display-color.service 2>/dev/null || true

echo
echo "Setup complete."
echo "Kiosk URL: http://127.0.0.1:8080/display/$SITE_SLUG"
echo "Logs: journalctl -u emic-kiosk -u emic-caddy --since today"
