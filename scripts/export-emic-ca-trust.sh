#!/usr/bin/env bash
# Export Caddy root CA for LAN clients (iPhone, iPad, etc.) and refresh caddy-trust/.
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

run_sudo() {
  if [ -f ~/.emic-deploy-sudo ]; then
    sudo -S "$@" < ~/.emic-deploy-sudo
    return
  fi
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
    return
  fi
  sudo "$@"
}

ensure_caddy_trust_writable() {
  mkdir -p caddy-trust
  if touch caddy-trust/.write-test 2>/dev/null; then
    rm -f caddy-trust/.write-test
    chmod 755 caddy-trust 2>/dev/null || true
    return
  fi
  run_sudo chown -R "$(whoami):$(whoami)" caddy-trust
  run_sudo chmod 755 caddy-trust
}

ensure_caddy_trust_writable

CADDY_ROOT="/data/caddy/pki/authorities/local/root.crt"

compose() {
  if [ -f ~/.emic-deploy-sudo ]; then
    sudo -S docker compose "$@" < ~/.emic-deploy-sudo
  elif docker info >/dev/null 2>&1; then
    docker compose "$@"
  elif groups | grep -q docker; then
    docker compose "$@"
  else
    run_sudo docker compose "$@"
  fi
}

tmp_ca="$(mktemp)"
if ! compose exec -T caddy cat "$CADDY_ROOT" > "$tmp_ca"; then
  rm -f "$tmp_ca"
  exit 1
fi

if ! install -m 644 "$tmp_ca" caddy-trust/emic-ca.crt 2>/dev/null; then
  run_sudo install -m 644 "$tmp_ca" caddy-trust/emic-ca.crt
  ensure_caddy_trust_writable
fi
rm -f "$tmp_ca"

tmp_mobileconfig="$(mktemp)"
python3 scripts/generate-emic-mobileconfig.py caddy-trust/emic-ca.crt "$tmp_mobileconfig"
install -m 644 "$tmp_mobileconfig" caddy-trust/emic-ca.mobileconfig
rm -f "$tmp_mobileconfig"
cp scripts/emic-ca-install.html caddy-trust/emic-ca.html
chmod 644 caddy-trust/emic-ca.crt caddy-trust/emic-ca.mobileconfig caddy-trust/emic-ca.html

echo "Exported caddy-trust bundle ($(wc -c < caddy-trust/emic-ca.crt) bytes CA)"
