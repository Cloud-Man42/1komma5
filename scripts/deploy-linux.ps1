# Deploy EMIC (Energy Monitoring In a Cloud) to Linux server via Docker
#
# Credentials are read from parameters or environment variables — never commit secrets.
#   EMIC_DEPLOY_SERVER, EMIC_DEPLOY_USER, EMIC_DEPLOY_PASSWORD
param(
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$RemoteDir = "energy-monitoring"
)

$ErrorActionPreference = "Stop"
$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"

if (-not $Server) { throw "Set EMIC_DEPLOY_SERVER or pass -Server" }
if (-not $User) { throw "Set EMIC_DEPLOY_USER or pass -User" }
if (-not $Password) { throw "Set EMIC_DEPLOY_PASSWORD or pass -Password" }
if (-not (Test-Path $plink)) { throw "PuTTY plink not found at $plink" }
if (-not (Test-Path $pscp)) { throw "PuTTY pscp not found at $pscp" }

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Creating deployment archive..."
$archive = Join-Path $env:TEMP "energy-monitoring-deploy.tar.gz"
if (Test-Path $archive) { Remove-Item $archive -Force }

# Exclude dev artifacts; include source needed for Docker build
$tarArgs = @(
    "-czf", $archive,
    "--exclude=frontend/node_modules",
    "--exclude=frontend/.next",
    "--exclude=.git",
    "--exclude=*.db",
    "--exclude=__pycache__",
    "--exclude=.venv",
    "--exclude=.env",
    "-C", $repoRoot,
    "backend", "collector", "frontend", "packages", "docker", "scripts", "alembic", "alembic.ini",
    "scripts/verify_mercedes_eqe_commands.py",
    "docker-compose.yml", "Caddyfile", "pyproject.toml", "uv.lock", ".env.production.example"
)

& tar @tarArgs
if ($LASTEXITCODE -ne 0) { throw "tar failed with exit code $LASTEXITCODE" }

Write-Host "Uploading to ${User}@${Server}..."
& $pscp -batch -pw $Password $archive "${User}@${Server}:${RemoteDir}.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "pscp upload failed" }

Write-Host "Extracting and starting Docker stack on server..."
$remoteCmd = "mkdir -p ~/$RemoteDir && rm -rf ~/$RemoteDir/frontend && tar -xzf ~/$RemoteDir.tar.gz -C ~/$RemoteDir && cd ~/$RemoteDir && if [ ! -f .env ]; then cp .env.production.example .env && POSTGRES_PASS=`$(openssl rand -hex 16) && sed -i `"s/CHANGE_ME/`$POSTGRES_PASS/`" .env && sed -i `"s/HEARTBEAT_PROVIDER=onekommafive/HEARTBEAT_PROVIDER=mock/`" .env && echo CADDY_DOMAIN=$Server >> .env && echo POSTGRES_PASSWORD=`$POSTGRES_PASS >> .env; fi && grep -q '^WIDGET_STALE_SECONDS=' .env 2>/dev/null || echo WIDGET_STALE_SECONDS=120 >> .env && grep -q '^WIDGET_SNAPSHOT_CACHE_SECONDS=' .env 2>/dev/null || echo WIDGET_SNAPSHOT_CACHE_SECONDS=15 >> .env && grep -q '^WIDGET_SAVINGS_CACHE_SECONDS=' .env 2>/dev/null || echo WIDGET_SAVINGS_CACHE_SECONDS=300 >> .env && grep -q '^WIDGET_RATE_LIMIT_PER_MINUTE=' .env 2>/dev/null || echo WIDGET_RATE_LIMIT_PER_MINUTE=60 >> .env && echo '$Password' | sudo -S docker compose build && echo '$Password' | sudo -S docker compose up -d && echo '$Password' | sudo -S docker compose restart caddy && echo '$Password' | sudo -S docker compose ps"

& $plink -batch -pw $Password "${User}@${Server}" $remoteCmd
if ($LASTEXITCODE -ne 0) { throw "Remote deploy failed" }

Remove-Item $archive -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Deploy complete. Application should be available at: http://${Server}/"
Write-Host "Config view: http://${Server}/config"
