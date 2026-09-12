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
    if echo "$SERVER" | grep -Eq '^[0-9.]+$'; then
      echo "CADDY_LAN_HOST=${SERVER}" >> .env
      echo "CADDY_DOMAIN=emic.inacloud.se" >> .env
    else
      echo "CADDY_DOMAIN=${SERVER}" >> .env
    fi
  fi
  echo "POSTGRES_PASSWORD=${POSTGRES_PASS}" >> .env
fi

grep -q '^WIDGET_STALE_SECONDS=' .env 2>/dev/null || echo WIDGET_STALE_SECONDS=120 >> .env

# Ensure Caddy TLS domain and LAN fallback on existing deployments.
if [ -n "$SERVER" ]; then
  if echo "$SERVER" | grep -Eq '^[0-9.]+$'; then
    if grep -q '^CADDY_LAN_HOST=' .env 2>/dev/null; then
      sed -i "s/^CADDY_LAN_HOST=.*/CADDY_LAN_HOST=${SERVER}/" .env
    else
      echo "CADDY_LAN_HOST=${SERVER}" >> .env
    fi
    if grep -q '^CADDY_DOMAIN=' .env 2>/dev/null; then
      sed -i 's/^CADDY_DOMAIN=.*/CADDY_DOMAIN=emic.inacloud.se/' .env
    else
      echo "CADDY_DOMAIN=emic.inacloud.se" >> .env
    fi
  else
    if grep -q '^CADDY_DOMAIN=' .env 2>/dev/null; then
      sed -i "s/^CADDY_DOMAIN=.*/CADDY_DOMAIN=${SERVER}/" .env
    else
      echo "CADDY_DOMAIN=${SERVER}" >> .env
    fi
  fi
fi

grep -q '^WIDGET_SNAPSHOT_CACHE_SECONDS=' .env 2>/dev/null || echo WIDGET_SNAPSHOT_CACHE_SECONDS=15 >> .env
grep -q '^WIDGET_SAVINGS_CACHE_SECONDS=' .env 2>/dev/null || echo WIDGET_SAVINGS_CACHE_SECONDS=300 >> .env
grep -q '^WIDGET_RATE_LIMIT_PER_MINUTE=' .env 2>/dev/null || echo WIDGET_RATE_LIMIT_PER_MINUTE=60 >> .env

# ChargeFinder (replaces legacy NOBIL_* variables)
sed -i '/^NOBIL_/d' .env 2>/dev/null || true
grep -q '^CHARGEFINDER_ENABLED=' .env 2>/dev/null || echo CHARGEFINDER_ENABLED=true >> .env
grep -q '^CHARGEFINDER_MODE=' .env 2>/dev/null || echo CHARGEFINDER_MODE=WEB >> .env
grep -q '^CHARGEFINDER_SEARCH_RADIUS_M=' .env 2>/dev/null || echo CHARGEFINDER_SEARCH_RADIUS_M=150 >> .env
grep -q '^CHARGEFINDER_TIMEOUT_SECONDS=' .env 2>/dev/null || echo CHARGEFINDER_TIMEOUT_SECONDS=15 >> .env
grep -q '^CHARGEFINDER_CACHE_TTL_SECONDS=' .env 2>/dev/null || echo CHARGEFINDER_CACHE_TTL_SECONDS=604800 >> .env
grep -q '^CHARGEFINDER_COOLDOWN_SECONDS=' .env 2>/dev/null || echo CHARGEFINDER_COOLDOWN_SECONDS=900 >> .env

grep -q '^SOLAR_FORECAST_SYNC_REFRESH_ON_READ=' .env 2>/dev/null || echo SOLAR_FORECAST_SYNC_REFRESH_ON_READ=false >> .env
grep -q '^FINANCIAL_AGGREGATES_ENABLED=' .env 2>/dev/null || echo FINANCIAL_AGGREGATES_ENABLED=true >> .env
grep -q '^DASHBOARD_REDIS_CACHE_TTL_SECONDS=' .env 2>/dev/null || echo DASHBOARD_REDIS_CACHE_TTL_SECONDS=60 >> .env
grep -q '^HORIZON_OPTIMIZER_REDIS_CACHE_TTL_SECONDS=' .env 2>/dev/null || echo HORIZON_OPTIMIZER_REDIS_CACHE_TTL_SECONDS=300 >> .env
grep -q '^TIMESCALE_RETENTION_ENABLED=' .env 2>/dev/null || echo TIMESCALE_RETENTION_ENABLED=true >> .env
if grep -q '^TIMESCALE_RETENTION_ENABLED=' .env 2>/dev/null; then
  sed -i 's/^TIMESCALE_RETENTION_ENABLED=.*/TIMESCALE_RETENTION_ENABLED=true/' .env
fi
grep -q '^TIMESCALE_COMPRESSION_ENABLED=' .env 2>/dev/null || echo TIMESCALE_COMPRESSION_ENABLED=true >> .env
if grep -q '^TIMESCALE_COMPRESSION_ENABLED=' .env 2>/dev/null; then
  sed -i 's/^TIMESCALE_COMPRESSION_ENABLED=.*/TIMESCALE_COMPRESSION_ENABLED=true/' .env
fi
grep -q '^SOLAR_FORECAST_L1_WARM_TTL_SECONDS=' .env 2>/dev/null || echo SOLAR_FORECAST_L1_WARM_TTL_SECONDS=300 >> .env
grep -q '^ENERGY_CONTROL_COLLECTOR_ENABLED=' .env 2>/dev/null || echo ENERGY_CONTROL_COLLECTOR_ENABLED=true >> .env
if grep -q '^ENERGY_CONTROL_PROVIDER=' .env 2>/dev/null; then
  sed -i 's/^ENERGY_CONTROL_PROVIDER=.*/ENERGY_CONTROL_PROVIDER=chargeamps/' .env
else
  echo ENERGY_CONTROL_PROVIDER=chargeamps >> .env
fi
if ! grep -q '^EMIC_ADMIN_TOKEN=.\+' .env 2>/dev/null; then
  echo "EMIC_ADMIN_TOKEN=$(openssl rand -hex 24)" >> .env
fi

# EMIC user authentication (cookie sessions + RBAC)
if grep -q '^EMIC_USER_AUTH_ENABLED=' .env 2>/dev/null; then
  sed -i 's/^EMIC_USER_AUTH_ENABLED=.*/EMIC_USER_AUTH_ENABLED=true/' .env
else
  echo EMIC_USER_AUTH_ENABLED=true >> .env
fi
grep -q '^EMIC_CORS_ORIGINS=' .env 2>/dev/null || echo EMIC_CORS_ORIGINS=https://emic.inacloud.se >> .env
grep -q '^EMIC_COOKIE_SECURE=' .env 2>/dev/null || echo EMIC_COOKIE_SECURE=true >> .env
grep -q '^EMIC_SESSION_TTL_HOURS=' .env 2>/dev/null || echo EMIC_SESSION_TTL_HOURS=8 >> .env
grep -q '^EMIC_LOGIN_MAX_ATTEMPTS=' .env 2>/dev/null || echo EMIC_LOGIN_MAX_ATTEMPTS=5 >> .env
grep -q '^EMIC_LOGIN_LOCKOUT_MINUTES=' .env 2>/dev/null || echo EMIC_LOGIN_LOCKOUT_MINUTES=15 >> .env
if grep -q '^NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=' .env 2>/dev/null; then
  sed -i 's/^NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=.*/NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=true/' .env
else
  echo NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=true >> .env
fi
if ! grep -q '^EMIC_BOOTSTRAP_ADMIN_EMAIL=.\+' .env 2>/dev/null; then
  echo "EMIC_BOOTSTRAP_ADMIN_EMAIL=admin@emic.inacloud.se" >> .env
fi
if ! grep -q '^EMIC_BOOTSTRAP_ADMIN_PASSWORD=.\+' .env 2>/dev/null; then
  echo "EMIC_BOOTSTRAP_ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)" >> .env
fi
grep -q '^MARKETPLACE_METADATA_ENABLED=' .env 2>/dev/null || echo MARKETPLACE_METADATA_ENABLED=true >> .env
grep -q '^MARKETPLACE_INTERNAL_CIDRS=' .env 2>/dev/null || echo 'MARKETPLACE_INTERNAL_CIDRS=192.168.0.0/16,10.0.0.0/8,172.16.0.0/12' >> .env
grep -q '^MARKETPLACE_STAGING_PATH=' .env 2>/dev/null || echo MARKETPLACE_STAGING_PATH=/var/lib/emic/marketplace/staging >> .env
grep -q '^EMIC_ALLOW_UNSIGNED_MODULES=' .env 2>/dev/null || echo EMIC_ALLOW_UNSIGNED_MODULES=false >> .env
grep -q '^MARKETPLACE_ARTIFACT_TLS_VERIFY=' .env 2>/dev/null || echo MARKETPLACE_ARTIFACT_TLS_VERIFY=false >> .env

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

if grep -q '^FINANCIAL_AGGREGATES_ENABLED=true' .env 2>/dev/null; then
  echo "Backfilling financial_daily aggregates..."
  run_docker exec -T backend python /app/scripts/backfill_financial_daily.py --site akarp --days 365 || true
fi

if grep -q '^TIMESCALE_RETENTION_ENABLED=true' .env 2>/dev/null; then
  echo "Ensuring TimescaleDB retention/compression policies..."
  run_docker exec -T backend python /app/scripts/ensure_timescale_policies.py || true
fi

run_docker ps

if [ -f ~/.emic-deploy-sudo ]; then
  rm -f ~/.emic-deploy-sudo
fi
