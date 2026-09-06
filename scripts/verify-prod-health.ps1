#!/usr/bin/env pwsh
# Post-deploy health check for Mercedes EQE + Charge Amps Halo stack.
param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$SiteSlug = "akarp",
    [double]$SolarKwhTolerance = 2.0,
    [int]$TimeoutSec = 20
)

$ErrorActionPreference = "Stop"
$failures = @()
$checks = @()

function Invoke-EmicApi {
    param([string]$Path)
    return Invoke-RestMethod -Uri "$BaseUrl$Path" -TimeoutSec $TimeoutSec
}

function Add-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $script:checks += [pscustomobject]@{ Name = $Name; Ok = $Ok; Detail = $Detail }
    if (-not $Ok) { $script:failures += "${Name}: ${Detail}" }
}

Write-Host "EMIC prod health check: $BaseUrl (site=$SiteSlug)"
Write-Host ""

try {
    $snapshot = Invoke-EmicApi "/api/sites/$SiteSlug/snapshot"
    Add-Check "snapshot" $true "site=$($snapshot.site.slug)"
} catch {
    Add-Check "snapshot" $false $_.Exception.Message
}

try {
    $dashboard = Invoke-EmicApi "/api/sites/$SiteSlug/dashboard"
    $produced = [double]$dashboard.today.produced_kwh
    Add-Check "dashboard" $true "produced_kwh=$produced"
} catch {
    Add-Check "dashboard" $false $_.Exception.Message
    $produced = $null
}

try {
    $forecast = Invoke-EmicApi "/api/sites/$SiteSlug/solar/forecast"
    $actual = [double]$forecast.actual_today_kwh
    if ($null -ne $produced) {
        $delta = [math]::Abs($actual - $produced)
        $aligned = $delta -le $SolarKwhTolerance
        Add-Check "solar/dashboard alignment" $aligned "forecast=$actual dashboard=$produced delta=$([math]::Round($delta,2)) kWh (tol=$SolarKwhTolerance)"
    } else {
        Add-Check "solar forecast" $true "actual_today_kwh=$actual"
    }
} catch {
    Add-Check "solar forecast" $false $_.Exception.Message
}

try {
    $vehicles = Invoke-EmicApi "/api/sites/$SiteSlug/vehicles/integration/status"
    $enabled = [bool]$vehicles.enabled
    Add-Check "mercedes integration" $enabled "enabled=$enabled health=$($vehicles.health_status)"
} catch {
    Add-Check "mercedes integration" $false $_.Exception.Message
}

try {
    $chargers = Invoke-EmicApi "/api/sites/$SiteSlug/ev-chargers"
    $count = @($chargers).Count
    $bridgeOk = $count -gt 0
    Add-Check "charge amps chargers" $bridgeOk "count=$count"
    if ($bridgeOk) {
        $bridge = Invoke-EmicApi "/api/sites/$SiteSlug/ev-chargers/$($chargers[0].id)/bridge-status"
        Add-Check "halo bridge status" $true "state=$($bridge.smart_charging_state) bridge_enabled=$($bridge.bridge_enabled)"
    }
} catch {
    Add-Check "charge amps / bridge" $false $_.Exception.Message
}

try {
    $health = Invoke-EmicApi "/api/sites/$SiteSlug/integration-health"
    Add-Check "integration health" $true "entries=$(@($health.integrations).Count)"
} catch {
    Add-Check "integration health" $false $_.Exception.Message
}

Write-Host ""
foreach ($check in $checks) {
    $mark = if ($check.Ok) { "OK" } else { "FAIL" }
    Write-Host "[$mark] $($check.Name): $($check.Detail)"
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "Health check failed ($($failures.Count) issue(s))."
    exit 1
}

Write-Host ""
Write-Host "All prod health checks passed."
exit 0
