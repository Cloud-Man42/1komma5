param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
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

$headers = @{ Authorization = "Bearer $AdminToken"; "Content-Type" = "application/json" }

Write-Host "Phase 22 AUTOMATIC readiness check ($Site @ $BaseUrl)"
$checks = @()

$status = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/status" -Headers $headers
$bridge = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/status" -Headers $headers
$mappings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/mappings" -Headers $headers
$preview = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/preview" -Method Post -Headers $headers -Body '{"action":"USE_NOW","target":"ev_charger"}'

function Add-Check($name, $ok, $detail) {
    $script:checks += [PSCustomObject]@{ Check = $name; Ok = $ok; Detail = $detail }
    $mark = if ($ok) { "OK" } else { "FAIL" }
    Write-Host ("  [{0}] {1} - {2}" -f $mark, $name, $detail)
}

Add-Check "SEMI_AUTOMATIC or higher" ($status.optimization_mode -in @("SEMI_AUTOMATIC", "AUTOMATIC")) $status.optimization_mode
Add-Check "control_enabled" ($status.control_enabled -eq $true) $status.control_enabled
Add-Check "heartbeat provider" ($status.provider -eq "heartbeat") $status.provider
Add-Check "bridge write_enabled" ($bridge.write_enabled -eq $true) $bridge.write_enabled
Add-Check "EV mappings" ($mappings.Count -gt 0) ("count=" + $mappings.Count)
Add-Check "setup class A-C" ($bridge.setup_classification -in @("A", "B", "C")) $bridge.setup_classification
Add-Check "preview PREVIEW" ($preview.outcome -eq "PREVIEW") $preview.outcome

$ready = ($checks | Where-Object { -not $_.Ok }).Count -eq 0
Write-Host ""
if ($ready) {
    Write-Host "All checks passed. AUTOMATIC rollout may be considered."
    exit 0
}
Write-Host "Not ready for AUTOMATIC. See docs/emic-analysis/phase22/00_AUTOMATIC_DECISION.md"
exit 1
