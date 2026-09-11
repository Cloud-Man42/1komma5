#!/usr/bin/env bash
set -euo pipefail
cd ~/energy-monitoring
cat > /tmp/sprint-a-governance-setup.sql <<'SQL'
INSERT INTO module_ownership (module_id, publisher_id, protected, created_at, updated_at)
VALUES ('sprint-a.ownership-test', 'sprint-a-owner-a', false, NOW(), NOW())
ON CONFLICT (module_id) DO UPDATE SET publisher_id = EXCLUDED.publisher_id, updated_at = NOW();
SQL
sudo -S sh -c 'cat /tmp/sprint-a-governance-setup.sql | docker compose exec -T postgres psql -U energy -d energy' < ~/.emic-deploy-sudo
sudo -S docker compose exec -T postgres psql -U energy -d energy -tAc "SELECT publisher_id FROM module_ownership WHERE module_id='sprint-a.ownership-test';" < ~/.emic-deploy-sudo
rm -f ~/.emic-deploy-sudo /tmp/sprint-a-governance-setup.sql
