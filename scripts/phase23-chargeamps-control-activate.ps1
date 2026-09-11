param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$Site = "akarp",
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $AdminToken) {
    . "$PSScriptRoot/lib/Get-EmicDeployCredential.ps1"
    $AdminToken = Get-EmicAdminTokenFromRemote
}

if (-not $AdminToken) {
    $envFile = Join-Path (Join-Path $PSScriptRoot "..") ".env"
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match '^EMIC_ADMIN_TOKEN=' } | Select-Object -First 1
        if ($line) { $AdminToken = ($line -split '=', 2)[1].Trim() }
    }
}

if (-not $AdminToken) {
    Write-Error "EMIC_ADMIN_TOKEN required (pass -AdminToken or set in .env)"
}

$headers = @{ Authorization = "Bearer $AdminToken"; "Content-Type" = "application/json" }

Write-Host "Phase 23: Charge Amps control provider activation for $Site"

$status = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/status" -Headers $headers
Write-Host "Current provider: $($status.provider) mode: $($status.optimization_mode)"

$preview = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/sites/$Site/energy-control/preview" `
    -Headers $headers `
    -Body (@{ action = "USE_NOW"; target = "ev_charger" } | ConvertTo-Json)

Write-Host "Preview outcome: $($preview.outcome) - $($preview.reason_sv)"
if ($preview.outcome -ne "PREVIEW") {
    Write-Warning "Expected PREVIEW. Check bridge_enabled on Charge Amps charger."
    exit 1
}

Write-Host "Charge Amps provider ready. Set ENERGY_CONTROL_PROVIDER=chargeamps in prod .env if not already."
