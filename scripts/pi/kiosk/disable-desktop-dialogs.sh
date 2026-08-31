#!/usr/bin/env bash
# Stop desktop components that can draw over the kiosk.
#
# A wall display has nobody to answer a prompt, so anything that can raise a
# window on top of Chromium must not run. Observed on this Pi:
#
#   - gnome-keyring's "Unlock Keyring / Authentication required" dialog
#   - squeekboard, the on-screen keyboard (the panel is a touchscreen)
#
# XDG autostart entries in /etc/xdg/autostart are masked per-user by placing a
# same-named entry with Hidden=true in ~/.config/autostart, which leaves the
# system packages untouched and is trivially reversible.
set -euo pipefail

AUTOSTART_DIR="${HOME}/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

# Keyring daemons are unnecessary because Chromium runs with
# --password-store=basic; leaving them enabled is what produced the unlock prompt.
MASK=(
  squeekboard
  gnome-keyring-pkcs11
  gnome-keyring-secrets
  gnome-keyring-ssh
  pprompt
  lxpolkit
  polkit-mate-authentication-agent-1
)

for name in "${MASK[@]}"; do
  target="$AUTOSTART_DIR/$name.desktop"
  cat >"$target" <<EOF
[Desktop Entry]
Type=Application
Name=$name (disabled by EMIC kiosk)
Exec=/bin/true
Hidden=true
X-GNOME-Autostart-enabled=false
EOF
  echo "masked $name"
done

# Anything already running from the current session.
for proc in squeekboard gnome-keyring-daemon lxpolkit polkit-mate-authentication-agent-1; do
  pkill -x "$proc" 2>/dev/null && echo "stopped $proc"
done

echo
echo "Masked autostart entries live in $AUTOSTART_DIR."
echo "Remove a file there to restore the corresponding desktop component."
