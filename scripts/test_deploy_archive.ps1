# Validates deploy archive excludes and lists critical paths.
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$archive = Join-Path $env:TEMP "energy-monitoring-deploy-test.tar.gz"
if (Test-Path $archive) { Remove-Item $archive -Force }

$tarArgs = @(
    "-czf", $archive,
    "--exclude=frontend/node_modules",
    "--exclude=frontend/.next",
    "--exclude=.git",
    "--exclude=*.db",
    "--exclude=__pycache__",
    "--exclude=.venv",
    "--exclude=.env",
    "--exclude=**/.build",
    "--exclude=**/.pytest_cache",
    "--exclude=**/pytest_cache",
    "--exclude=**/__pycache__",
    "--exclude=packages/energy-core/tests",
    "--exclude=backend/tests",
    "--exclude=collector/tests",
    "-C", $repoRoot,
    "backend", "collector", "frontend", "packages", "docker", "scripts", "alembic", "alembic.ini",
    "scripts/verify_mercedes_eqe_commands.py",
    "scripts/deploy-linux-remote.sh",
    "scripts/deploy-linux-extract.sh",
    "docker-compose.yml", "Caddyfile", "pyproject.toml", "uv.lock", ".env.production.example"
)

& tar @tarArgs
if ($LASTEXITCODE -ne 0) { throw "tar failed" }

$listing = & tar -tzf $archive
if ($listing -match '\.build/') {
    throw "Archive must not contain .build directories"
}

$required = @(
    "backend/app/main.py",
    "frontend/package.json",
    "packages/energy-core/pyproject.toml",
    "scripts/deploy-linux-extract.sh"
)
foreach ($path in $required) {
    if (-not ($listing -match [regex]::Escape($path))) {
        throw "Archive missing required path: $path"
    }
}

$hash = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToLower()
if ($hash.Length -ne 64) { throw "Invalid SHA256" }

Write-Host "deploy archive validation PASS"
Write-Host "  size=$((Get-Item $archive).Length) bytes"
Write-Host "  sha256=$hash"
Remove-Item $archive -Force
