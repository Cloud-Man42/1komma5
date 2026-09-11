#!/usr/bin/env bash
set -eu
cd ~/energy-monitoring
echo "$1" | sudo -S docker compose exec -T postgres psql -U energy -d energy -c "UPDATE installed_module_packages SET package_state='installed' WHERE module_id='integration.sensibo';"
echo "$1" | sudo -S docker compose exec -T postgres psql -U energy -d energy -c "SELECT module_id, package_state, checksum_sha256 FROM installed_module_packages WHERE module_id='integration.sensibo';"
echo "$1" | sudo -S docker compose restart backend collector
