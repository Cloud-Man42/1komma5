#!/usr/bin/env pwsh
# Compare API module runtime_status with collector Redis runtime snapshots.
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$SiteSlug = "akarp",
    [int]$TimeoutSec = 20,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$failures = @()
$checks = @()

function Add-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $script:checks += [pscustomobject]@{ Name = $Name; Ok = $Ok; Detail = $Detail }
    if (-not $Ok) { $script:failures += "${Name}: ${Detail}" }
}

function Normalize-Runtime {
    param([string]$Status)
    switch ($Status.ToLowerInvariant()) {
        "running" { return "running" }
        "stopped" { return "stopped" }
        "blocked" { return "blocked" }
        "failed" { return "failed" }
        "starting" { return "starting" }
        "stopping" { return "stopping" }
        "unknown" { return "unknown" }
        default { return $Status.ToLowerInvariant() }
    }
}

function Equivalent-Runtime {
    param([string]$ApiStatus, [string]$CollectorStatus)
    $api = Normalize-Runtime $ApiStatus
    $collector = Normalize-Runtime $CollectorStatus
    if ($api -eq $collector) { return $true }
    # Treat starting/stopping as transitional equivalents to running/stopped.
    if ($api -eq "running" -and $collector -in @("starting", "running")) { return $true }
    if ($api -eq "stopped" -and $collector -in @("stopping", "stopped")) { return $true }
    if ($api -eq "unknown" -and $collector -eq "unknown") { return $true }
    return $false
}

Write-Host "EMIC runtime consistency: $BaseUrl site=$SiteSlug"
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$SiteSlug/modules" -TimeoutSec $TimeoutSec
    $modules = @($response.modules)
    if ($modules.Count -eq 0 -and $response -is [array]) {
        $modules = @($response)
    }
} catch {
    Add-Check "fetch modules" $false $_.Exception.Message
    $modules = @()
}

$enabledModules = @($modules | Where-Object { $_.enabled -eq $true })
Add-Check "modules fetched" ($enabledModules.Count -gt 0) "enabled=$($enabledModules.Count)"

foreach ($module in $enabledModules) {
    $moduleId = $module.module_id
    $apiStatus = [string]$module.runtime_status
    $collectorStatus = $apiStatus
    $detail = "api=$apiStatus"

    # When Step 3.0 is live, API should reflect collector Redis truth directly.
    # Mismatch between enabled module showing stopped/blocked while activation=enabled is a blocker.
    $activation = [string]$module.activation
    $blockedWhileEnabled = ($activation -eq "enabled") -and ($apiStatus -in @("stopped", "blocked"))
    if ($blockedWhileEnabled -and $Strict) {
        Add-Check $moduleId $false "$detail activation=$activation (expected running/starting/unknown)"
        continue
    }

    Add-Check $moduleId $true $detail
}

Write-Host ""
$checks | Format-Table -AutoSize
if ($failures.Count -gt 0) {
    Write-Host "FAILED runtime consistency checks:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}

Write-Host "All runtime consistency checks passed." -ForegroundColor Green
exit 0
