# Deploy EMIC (Energy Monitoring In a Cloud) to Linux server via Docker
#
# Authentication (pick one):
#   EMIC_DEPLOY_KEY          — PuTTY private key (.ppk) for plink/pscp (preferred)
#   EMIC_DEPLOY_PASSWORD_FILE — file containing SSH password (used with plink -pw)
#   EMIC_DEPLOY_PASSWORD     — SSH password (fallback; avoid in shared shells)
#
# Optional sudo on remote when user is not in the docker group:
#   EMIC_DEPLOY_SUDO_PASSWORD_FILE — uploaded to ~/.emic-deploy-sudo (mode 600), never passed on CLI
param(
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$KeyFile = $env:EMIC_DEPLOY_KEY,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE,
    [string]$RemoteDir = "energy-monitoring"
)

$ErrorActionPreference = "Stop"
$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"

if (-not $Server) { throw "Set EMIC_DEPLOY_SERVER or pass -Server" }
if (-not $User) { throw "Set EMIC_DEPLOY_USER or pass -User" }
if (-not (Test-Path $plink)) { throw "PuTTY plink not found at $plink" }
if (-not (Test-Path $pscp)) { throw "PuTTY pscp not found at $pscp" }

if ($PasswordFile) {
    if (-not (Test-Path $PasswordFile)) { throw "Password file not found: $PasswordFile" }
    $Password = (Get-Content -Path $PasswordFile -Raw).Trim()
}

$authArgs = @()
if ($KeyFile) {
    if (-not (Test-Path $KeyFile)) { throw "Key file not found: $KeyFile" }
    $authArgs = @("-batch", "-i", $KeyFile)
} elseif ($Password) {
    $authArgs = @("-batch", "-pw", $Password)
} else {
    throw "Set EMIC_DEPLOY_KEY, EMIC_DEPLOY_PASSWORD_FILE, or EMIC_DEPLOY_PASSWORD"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Creating deployment archive..."
$archive = Join-Path $env:TEMP "energy-monitoring-deploy.tar.gz"
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
    "-C", $repoRoot,
    "backend", "collector", "frontend", "packages", "docker", "scripts", "alembic", "alembic.ini",
    "scripts/verify_mercedes_eqe_commands.py",
    "scripts/deploy-linux-remote.sh",
    "docker-compose.yml", "Caddyfile", "pyproject.toml", "uv.lock", ".env.production.example"
)

$ErrorActionPreference = "Continue"

& tar @tarArgs
if ($LASTEXITCODE -ne 0) { throw "tar failed with exit code $LASTEXITCODE" }

Write-Host "Uploading to ${User}@${Server}..."
& $pscp @authArgs $archive "${User}@${Server}:${RemoteDir}.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "pscp upload failed" }

$remoteScript = Join-Path $repoRoot "scripts/deploy-linux-remote.sh"
$remoteScriptUnix = Join-Path $env:TEMP "deploy-linux-remote-unix.sh"
$unixContent = (Get-Content -Path $remoteScript -Raw).Replace("`r`n", "`n")
[System.IO.File]::WriteAllText($remoteScriptUnix, $unixContent)
& $pscp @authArgs $remoteScriptUnix "${User}@${Server}:deploy-linux-remote.sh"
if ($LASTEXITCODE -ne 0) { throw "pscp script upload failed" }

if ($SudoPasswordFile) {
    if (-not (Test-Path $SudoPasswordFile)) { throw "Sudo password file not found: $SudoPasswordFile" }
    & $pscp @authArgs $SudoPasswordFile "${User}@${Server}:.emic-deploy-sudo"
    if ($LASTEXITCODE -ne 0) { throw "pscp sudo password upload failed" }
    & $plink @authArgs "${User}@${Server}" "chmod 600 ~/.emic-deploy-sudo"
    if ($LASTEXITCODE -ne 0) { throw "chmod on remote sudo password file failed" }
}

Write-Host "Extracting and starting Docker stack on server..."
$extractCmd = "mkdir -p ~/$RemoteDir && rm -rf ~/$RemoteDir/frontend && tar -xzf ~/$RemoteDir.tar.gz -C ~/$RemoteDir && cp ~/deploy-linux-remote.sh ~/$RemoteDir/deploy-linux-remote.sh && chmod +x ~/$RemoteDir/deploy-linux-remote.sh"
& $plink @authArgs "${User}@${Server}" $extractCmd
if ($LASTEXITCODE -ne 0) { throw "Remote extract failed" }

& $plink @authArgs "${User}@${Server}" "bash ~/$RemoteDir/deploy-linux-remote.sh $RemoteDir $Server"
if ($LASTEXITCODE -ne 0) { throw "Remote deploy failed" }

Remove-Item $archive -Force -ErrorAction SilentlyContinue
Write-Host ""
$scheme = if ($Server -match '^[0-9.]+$') { "http" } else { "https" }
Write-Host "Deploy complete. Application should be available at: ${scheme}://${Server}/"
Write-Host "Config view: ${scheme}://${Server}/config"
if ($Server -match '^[0-9.]+$') {
  Write-Host "Tip: set CADDY_DOMAIN=emic.inacloud.se in .env on the server for HTTPS via Let's Encrypt."
}
