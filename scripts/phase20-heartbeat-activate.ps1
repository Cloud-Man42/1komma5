param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE
)

$ErrorActionPreference = "Stop"

if ($PasswordFile -and (Test-Path $PasswordFile)) {
    $Password = (Get-Content -Path $PasswordFile -Raw).Trim()
}

if (-not $Server) { $Server = ([uri]$BaseUrl).Host }
if (-not $User) { $User = "hm" }

function Invoke-RemoteEnv {
    param([string]$Pattern)
    $plink = "C:\Program Files\PuTTY\plink.exe"
    if (-not (Test-Path $plink)) { throw "PuTTY plink not found" }
    $authArgs = @("-batch", "-pw", $Password)
    $cmd = "grep -E '^$Pattern=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-"
    return (& $plink @authArgs "${User}@${Server}" $cmd).Trim()
}

Write-Host "Phase 20 step 1 - Heartbeat RECOMMEND activation on $BaseUrl site=$Site"

$adminToken = Invoke-RemoteEnv -Pattern "EMIC_ADMIN_TOKEN"
if (-not $adminToken) {
    Write-Warning "EMIC_ADMIN_TOKEN empty on server; settings update may be open."
}

$headers = @{ "Content-Type" = "application/json" }
if ($adminToken) {
    $headers["Authorization"] = "Bearer $adminToken"
}

$settingsBody = @{ optimization_mode = "RECOMMEND" } | ConvertTo-Json
$settingsUrl = "$BaseUrl/api/sites/$Site/energy-control/settings"
Write-Host "PUT $settingsUrl"
$settingsRes = Invoke-RestMethod -Uri $settingsUrl -Method Put -Headers $headers -Body $settingsBody
Write-Host ("  mode={0} provider={1} writes_allowed={2}" -f $settingsRes.optimization_mode, $settingsRes.provider, $settingsRes.writes_allowed)

$status = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/status"
Write-Host ("Status: mode={0} provider={1}" -f $status.optimization_mode, $status.provider)

if ($status.optimization_mode -ne "RECOMMEND") {
    throw "Expected RECOMMEND mode, got $($status.optimization_mode)"
}
if ($status.provider -ne "heartbeat") {
    Write-Warning "Expected heartbeat provider, got $($status.provider); redeploy may be required."
}

Write-Host "Heartbeat RECOMMEND activation OK."
