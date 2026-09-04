param(
    [string]$BaseUrl = "http://192.168.50.54",
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

$headers = @{ Authorization = "Bearer $AdminToken" }
Write-Host "Phase 25 Timescale policy verify @ $BaseUrl"
$status = Invoke-RestMethod -Uri "$BaseUrl/api/system/timescale-status" -Headers $headers
$status | ConvertTo-Json -Depth 5

if ($status.status -ne "ok") {
    Write-Host "Timescale policies incomplete or skipped."
    exit 1
}
Write-Host "Timescale retention + compression OK."
