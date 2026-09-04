param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN
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

Write-Host "Phase 25 AUTOMATIC monitor ($Site @ $BaseUrl)"
$status = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/status" -Headers $headers
$recent = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/recent?limit=5" -Headers $headers

Write-Host ("  mode={0} provider={1} automatic_allowed={2}" -f $status.optimization_mode, $status.provider, $status.automatic_allowed)
if ($status.last_action) {
    Write-Host ("  last_action={0} outcome={1} at={2}" -f $status.last_action.action, $status.last_action.outcome, $status.last_action.recorded_at)
}

$applied = @($recent.items | Where-Object { $_.outcome -eq "APPLIED" })
Write-Host ("  recent APPLIED count (last 5)={0}" -f $applied.Count)

$ok = $status.optimization_mode -eq "AUTOMATIC" -and $status.automatic_allowed -and $status.provider -eq "chargeamps"
if (-not $ok) {
    Write-Host "AUTOMATIC monitor: FAIL"
    exit 1
}
Write-Host "AUTOMATIC monitor: OK"
