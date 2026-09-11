param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $AdminToken) {
    . "$PSScriptRoot/lib/Get-EmicDeployCredential.ps1"
    $AdminToken = Get-EmicAdminTokenFromRemote
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
