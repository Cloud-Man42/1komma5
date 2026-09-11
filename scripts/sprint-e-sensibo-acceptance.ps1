#!/usr/bin/env pwsh
# Sprint E Sensibo acceptance (prod / staging)
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN,
    [string]$SiteSlug = "akarp",
    [int]$TimeoutSec = 30
)

$ErrorActionPreference = "Stop"
$failures = @()
$checks = @()

function Add-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $script:checks += [pscustomobject]@{ Name = $Name; Ok = $Ok; Detail = $Detail }
    if (-not $Ok) { $script:failures += "${Name}: ${Detail}" }
}

if (-not $AdminToken) {
    Write-Host "EMIC_ADMIN_TOKEN not set."
    exit 2
}

$headers = @{ Authorization = "Bearer $AdminToken" }

Write-Host "Sprint E Sensibo acceptance: $BaseUrl site=$SiteSlug"
Write-Host ""

try {
    $flags = Invoke-RestMethod -Uri "$BaseUrl/api/system/modules" -Headers $headers -TimeoutSec $TimeoutSec
    $thirdParty = [bool]$flags.third_party_runtime_enabled
    Add-Check "third_party_runtime_enabled stays false" (-not $thirdParty) "value=$thirdParty"
} catch {
    Add-Check "runtime flags" $false $_.Exception.Message
}

try {
    $detail = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/integration.sensibo" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "sensibo store detail" ($detail.summary.module_id -eq "integration.sensibo") $detail.summary.display_name
} catch {
    Add-Check "sensibo store detail" $false $_.Exception.Message
}

try {
    $preflight = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/integration.sensibo/1.0.0/preflight" `
        -Method POST -Headers ($headers + @{ "Content-Type" = "application/json" }) `
        -Body (@{ site_slug = $SiteSlug } | ConvertTo-Json) -TimeoutSec $TimeoutSec
    Add-Check "sensibo preflight allow" ($preflight.policy.decision -eq "ALLOW") $preflight.policy.decision
} catch {
    Add-Check "sensibo preflight" $false $_.Exception.Message
}

try {
    $auths = Invoke-RestMethod -Uri "$BaseUrl/api/modules/runtime/authorizations" -Headers $headers -TimeoutSec $TimeoutSec
    $sensiboAuth = @($auths | Where-Object { $_.module_id -eq "integration.sensibo" -and $_.site_id -ge 1 })
    Add-Check "runtime authorization present" ($sensiboAuth.Count -ge 1) "count=$($sensiboAuth.Count)"
} catch {
    Add-Check "runtime authorization list" $false $_.Exception.Message
}

try {
    $climate = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$SiteSlug/climate/devices" -TimeoutSec $TimeoutSec
    $count = @($climate.devices).Count
    Add-Check "climate devices api" ($null -ne $climate.devices) "devices=$count"
} catch {
    Add-Check "climate devices api" $false $_.Exception.Message
}

try {
    $config = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$SiteSlug/modules/integration.sensibo/external-config" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "external config readable" ($null -ne $config.credential_configured) "configured=$($config.credential_configured)"
} catch {
    Add-Check "external config" $false $_.Exception.Message
}

Write-Host ""
foreach ($c in $checks) {
    $mark = if ($c.Ok) { "PASS" } else { "FAIL" }
    Write-Host "[$mark] $($c.Name) - $($c.Detail)"
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "FAILED ($($failures.Count) checks)"
    exit 1
}

Write-Host ""
Write-Host "Sprint E acceptance checks passed (operator must still verify live Sensibo readings + logs)."
exit 0
