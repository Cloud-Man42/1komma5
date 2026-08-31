#!/usr/bin/env bash
set -euo pipefail

REMOTE_DIR="${1:-energy-monitoring}"
SERVER="${2:-}"

cd ~/"$REMOTE_DIR"

if [ ! -f .env ]; then
  cp .env.production.example .env
  POSTGRES_PASS="$(openssl rand -hex 16)"
  sed -i "s/CHANGE_ME/${POSTGRES_PASS}/" .env
  sed -i "s/HEARTBEAT_PROVIDER=onekommafive/HEARTBEAT_PROVIDER=mock/" .env
  if [ -n "$SERVER" ]; then
    echo "CADDY_DOMAIN=${SERVER}" >> .env
  fi
  echo "POSTGRES_PASSWORD=${POSTGRES_PASS}" >> .env
fi

grep -q '^WIDGET_STALE_SECONDS=' .env 2>/dev/null || echo WIDGET_STALE_SECONDS=120 >> .env
grep -q '^WIDGET_SNAPSHOT_CACHE_SECONDS=' .env 2>/dev/null || echo WIDGET_SNAPSHOT_CACHE_SECONDS=15 >> .env
grep -q '^WIDGET_SAVINGS_CACHE_SECONDS=' .env 2>/dev/null || echo WIDGET_SAVINGS_CACHE_SECONDS=300 >> .env
grep -q '^WIDGET_RATE_LIMIT_PER_MINUTE=' .env 2>/dev/null || echo WIDGET_RATE_LIMIT_PER_MINUTE=60 >> .env

run_docker() {
  if [ -f ~/.emic-deploy-sudo ]; then
    sudo -S docker compose "$@" < ~/.emic-deploy-sudo
    return
  fi
  if docker info >/dev/null 2>&1; then
    docker compose "$@"
    return
  fi
  if groups | grep -q docker; then
    docker compose "$@"
    return
  fi
  sudo docker compose "$@"
}

run_docker build
run_docker up -d
run_docker restart caddy
run_docker ps

if [ -f ~/.emic-deploy-sudo ]; then
  rm -f ~/.emic-deploy-sudo
fi
