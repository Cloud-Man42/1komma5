param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN,
    [switch]$SkipApply
)

$ErrorActionPreference = "Stop"

if (-not $AdminToken) {
    $plink = "C:\Program Files\PuTTY\plink.exe"
    $pw = $env:EMIC_DEPLOY_PASSWORD
    if (-not $pw) { $pw = "mathias3" }
    if (Test-Path $plink) {
        $AdminToken = (& $plink -batch -pw $pw hm@192.168.50.54 "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
    }
}
if (-not $AdminToken) { throw "EMIC_ADMIN_TOKEN required" }

$headers = @{ Authorization = "Bearer $AdminToken"; "Content-Type" = "application/json" }

Write-Host "Phase 24 - Charge Amps AUTOMATIC activation on $BaseUrl site=$Site"

& (Join-Path $PSScriptRoot "phase24-chargeamps-automatic-readiness.ps1") -BaseUrl $BaseUrl -Site $Site -AdminToken $AdminToken
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$previewBody = @{ action = "USE_NOW"; target = "ev_charger" } | ConvertTo-Json
$preview = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/preview" -Method Post -Headers $headers -Body $previewBody
Write-Host ("  preview outcome={0} provider={1}" -f $preview.outcome, $preview.provider)
if ($preview.reason_sv) { Write-Host ("  preview: {0}" -f $preview.reason_sv) }

if (-not $SkipApply) {
    $apply = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/apply" -Method Post -Headers $headers -Body $previewBody
    Write-Host ("  apply outcome={0} provider={1}" -f $apply.outcome, $apply.provider)
    if ($apply.reason_sv) { Write-Host ("  apply: {0}" -f $apply.reason_sv) }
    if ($apply.outcome -notin @("APPLIED", "FAILED")) {
        Write-Warning "Apply did not reach charger (outcome=$($apply.outcome)). AUTOMATIC may still be enabled if preview OK."
    }
}

$settingsBody = @{ optimization_mode = "AUTOMATIC"; control_enabled = $true } | ConvertTo-Json
$settings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/settings" -Method Put -Headers $headers -Body $settingsBody
Write-Host ("  mode={0} control={1} automatic_allowed={2} provider={3}" -f $settings.optimization_mode, $settings.control_enabled, $settings.automatic_allowed, $settings.provider)

if ($settings.optimization_mode -ne "AUTOMATIC" -or -not $settings.automatic_allowed) {
    Write-Error "AUTOMATIC mode was not enabled."
}

Write-Host "Phase 24 AUTOMATIC activation complete."
