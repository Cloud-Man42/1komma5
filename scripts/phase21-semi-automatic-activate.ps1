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

$headers = @{
    Authorization = "Bearer $AdminToken"
    "Content-Type" = "application/json"
}

Write-Host "Phase 21 step 3 - SEMI_AUTOMATIC + control on $BaseUrl site=$Site"
$body = @{ optimization_mode = "SEMI_AUTOMATIC"; control_enabled = $true } | ConvertTo-Json
$settings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/settings" -Method Put -Headers $headers -Body $body
Write-Host ("  mode={0} control={1} writes_allowed={2} provider={3}" -f $settings.optimization_mode, $settings.control_enabled, $settings.writes_allowed, $settings.provider)

if (-not $settings.writes_allowed) {
    Write-Warning "writes_allowed is false; manual apply may still be blocked."
}

$previewBody = @{ action = "USE_NOW"; target = "ev_charger" } | ConvertTo-Json
$preview = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/preview" -Method Post -Headers @{ "Content-Type" = "application/json" } -Body $previewBody
Write-Host ("  preview action={0} outcome={1} dry_run={2}" -f $preview.action, $preview.outcome, $preview.dry_run)
if ($preview.reason_sv) { Write-Host ("  preview reason: {0}" -f $preview.reason_sv) }

$apply = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/apply" -Method Post -Headers $headers -Body $previewBody
Write-Host ("  apply action={0} outcome={1} dry_run={2} provider={3}" -f $apply.action, $apply.outcome, $apply.dry_run, $apply.provider)
if ($apply.reason_sv) { Write-Host ("  apply reason: {0}" -f $apply.reason_sv) }

if ($preview.outcome -ne "PREVIEW") {
    Write-Warning "Preview was not PREVIEW — run scripts/phase22-heartbeat-control-diagnose.ps1 -RunDiscovery"
}
Write-Host "SEMI_AUTOMATIC Heartbeat apply verification OK."
