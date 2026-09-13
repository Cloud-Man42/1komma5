# Trust the EMIC Caddy internal CA on this Windows machine.
# Required for https://emic.inacloud.se without browser/PWA SSL errors on LAN.
#
# Usage:
#   .\scripts\trust-emic-caddy-ca.ps1
#   .\scripts\trust-emic-caddy-ca.ps1 -MachineStore   # requires admin

param(
    [string]$Server = $(if ($env:EMIC_DEPLOY_SERVER) { $env:EMIC_DEPLOY_SERVER } else { "192.168.50.54" }),
    [string]$User = $(if ($env:EMIC_DEPLOY_USER) { $env:EMIC_DEPLOY_USER } else { "hm" }),
    [switch]$MachineStore
)

$ErrorActionPreference = "Stop"

$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"
if (-not (Test-Path $plink)) { throw "PuTTY plink not found at $plink" }

$passwordFile = Join-Path $env:USERPROFILE ".emic-deploy-password"
$sudoFile = Join-Path $env:USERPROFILE ".emic-deploy-sudo"
if (-not (Test-Path $passwordFile)) { throw "Missing $passwordFile" }
if (-not (Test-Path $sudoFile)) { throw "Missing $sudoFile" }

$pw = (Get-Content $passwordFile -Raw).Trim()
$sudoRaw = (Get-Content $sudoFile -Raw).Trim()
$sudoUnix = Join-Path $env:TEMP "emic-deploy-sudo-unix"
$certPath = Join-Path $env:TEMP "emic-caddy-root.crt"
$caddyRoot = "/data/caddy/pki/authorities/local/root.crt"

[System.IO.File]::WriteAllText($sudoUnix, $sudoRaw)
& $pscp -batch -pw $pw $sudoUnix "${User}@${Server}:.emic-deploy-sudo" | Out-Null
$remoteCert = "/home/$User/emic-caddy-root.crt"
$remoteCmd = "cd ~/energy-monitoring && sudo -S bash -c 'docker compose exec -T caddy cat $caddyRoot > $remoteCert && chmod 644 $remoteCert' < ~/.emic-deploy-sudo && rm -f ~/.emic-deploy-sudo"
& $plink -batch -pw $pw "${User}@${Server}" $remoteCmd | Out-Null
& $pscp -batch -pw $pw "${User}@${Server}:emic-caddy-root.crt" $certPath | Out-Null
if (-not (Test-Path $certPath) -or (Get-Content $certPath -Raw) -notmatch "BEGIN CERTIFICATE") {
    throw "Failed to download Caddy root CA from $Server"
}

if ($MachineStore) {
    certutil -addstore Root $certPath | Out-Null
    Write-Host "Installed EMIC Caddy CA into Local Machine Trusted Root (all users)."
} else {
    certutil -addstore -user Root $certPath | Out-Null
    Write-Host "Installed EMIC Caddy CA into Current User Trusted Root."
}

# Windows Schannel may fail revocation checks for Caddy's local CA; --ssl-no-revoke matches browser leniency.
$probe = curl.exe --ssl-no-revoke -s -o NUL -w "%{http_code}" "https://emic.inacloud.se/health"
if ($probe -ne "200") {
    Write-Warning "HTTPS probe returned $probe - restart browser and clear site data for emic.inacloud.se if issues remain."
} else {
    Write-Host "HTTPS probe OK (200). Restart browser, then open https://emic.inacloud.se/login"
}
