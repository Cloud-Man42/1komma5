param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [switch]$RunDiscovery,
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $AdminToken) {
    $plink = "C:\Program Files\PuTTY\plink.exe"
    $pw = $env:EMIC_DEPLOY_PASSWORD
    if ($pw -and (Test-Path $plink)) {
        $AdminToken = (& $plink -batch -pw $pw hm@192.168.50.54 "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
    }
}
if (-not $AdminToken) { throw "EMIC_ADMIN_TOKEN required" }

$headers = @{
    Authorization = "Bearer $AdminToken"
    "Content-Type" = "application/json"
}

function Show-Json($label, $obj) {
    Write-Host ""
    Write-Host "== $label =="
    $obj | ConvertTo-Json -Depth 6
}

Write-Host "Phase 22 - Heartbeat control diagnose on $BaseUrl site=$Site"

$status = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/status" -Headers $headers
Show-Json "energy-control/status" $status

$bridge = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/status" -Headers $headers
Show-Json "heartbeat/bridge/status" $bridge

$settings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/settings" -Headers $headers
Show-Json "heartbeat/bridge/settings" $settings

$mappings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/mappings" -Headers $headers
Show-Json "heartbeat/bridge/mappings" $mappings

if ($RunDiscovery -or $mappings.Count -eq 0) {
    Write-Host ""
    Write-Host "Running Heartbeat discovery..."
    $discovery = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/discovery/run" -Method Post -Headers $headers
    Show-Json "discovery/run" $discovery
    $mappings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/mappings" -Headers $headers
    Show-Json "heartbeat/bridge/mappings (after discovery)" $mappings
}

$previewBody = @{ action = "USE_NOW"; target = "ev_charger" } | ConvertTo-Json
$preview = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/preview" -Method Post -Headers $headers -Body $previewBody
Show-Json "energy-control/preview" $preview

if ($status.writes_allowed -and $preview.outcome -eq "PREVIEW") {
    Write-Host ""
    Write-Host "Preview OK. To apply manually when EV is plugged in:"
    Write-Host "  POST $BaseUrl/api/sites/$Site/energy-control/apply"
    Write-Host '  body: {"action":"USE_NOW","target":"ev_charger"}'
}

if ($preview.outcome -eq "REJECTED") {
    Write-Host ""
    Write-Host "REJECTED: $($preview.reason_sv) ($($preview.reason))"
    if ($mappings.Count -eq 0) {
        Write-Host "Fix: run discovery with -RunDiscovery, link mapping to charger, enable write_enabled in bridge settings."
    }
    if (-not $settings.write_enabled) {
        Write-Host "Note: write_enabled=false - apply will reject even after mapping exists."
    }
}
