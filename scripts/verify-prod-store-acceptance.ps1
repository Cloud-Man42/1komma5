#!/usr/bin/env pwsh
# Production Store acceptance smoke tests (Sprint D.5)
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN,
    [int]$TimeoutSec = 20
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
    Write-Host "EMIC_ADMIN_TOKEN not set - pass -AdminToken or set EMIC_ADMIN_TOKEN."
    exit 2
}

$headers = @{ Authorization = "Bearer $AdminToken" }

Write-Host "Store prod acceptance: $BaseUrl"
Write-Host ""

try {
    Invoke-RestMethod -Uri "$BaseUrl/api/modules/store" -TimeoutSec $TimeoutSec | Out-Null
    Add-Check "store api anonymous denied" $false "unexpected 200"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Add-Check "store api anonymous denied" ($code -in 401, 403) "status=$code"
}

try {
    $catalog = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?page_size=5" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store catalog admin" ($null -ne $catalog.modules) "total=$($catalog.total)"
} catch {
    Add-Check "store catalog admin" $false $_.Exception.Message
}

try {
    $status = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/status" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store status" ($null -ne $status.message) $status.message
} catch {
    Add-Check "store status" $false $_.Exception.Message
}

try {
    $page = Invoke-WebRequest -Uri "$BaseUrl/config/modules-devices/store" -TimeoutSec $TimeoutSec -UseBasicParsing
    $hasShell = $page.Content -match "Module Store|Discover|modules-devices/store"
    Add-Check "store ui route" (($page.StatusCode -eq 200) -and $hasShell) "status=$($page.StatusCode)"
} catch {
    Add-Check "store ui route" $false $_.Exception.Message
}

try {
    $search = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?search=charge" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store search" ($search.total -ge 1) "total=$($search.total)"
} catch {
    Add-Check "store search" $false $_.Exception.Message
}

try {
    $noResult = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?search=zzznomatch999" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store search no result" ($noResult.total -eq 0) "total=$($noResult.total)"
} catch {
    Add-Check "store search no result" $false $_.Exception.Message
}

try {
    $category = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?category=EV%20Charging" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store category filter" ($category.total -ge 1) "total=$($category.total)"
} catch {
    Add-Check "store category filter" $false $_.Exception.Message
}

try {
    $official = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?official=true" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store official filter" ($official.total -ge 1) "total=$($official.total)"
} catch {
    Add-Check "store official filter" $false $_.Exception.Message
}

try {
    $installed = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?installed=true" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store installed filter" ($installed.total -ge 1) "total=$($installed.total)"
} catch {
    Add-Check "store installed filter" $false $_.Exception.Message
}

try {
    $control = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?control_capable=true" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store control filter" ($control.total -ge 1) "total=$($control.total)"
} catch {
    Add-Check "store control filter" $false $_.Exception.Message
}

try {
    $updates = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store?update_available=true" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "store updates empty state" ($updates.total -eq 0) "total=$($updates.total)"
} catch {
    Add-Check "store updates empty state" $false $_.Exception.Message
}

try {
    $detail = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/integration.chargeamps" -Headers $headers -TimeoutSec $TimeoutSec
    $detailOk = ($detail.summary.trust_tier -eq "OFFICIAL") -and ($null -ne $detail.capabilities)
    Add-Check "module detail builtin" $detailOk "module=$($detail.summary.module_id)"
} catch {
    Add-Check "module detail builtin" $false $_.Exception.Message
}

try {
    $publishers = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/publishers" -Headers $headers -TimeoutSec $TimeoutSec
    $pubId = $publishers[0].publisher_id
    $pubDetail = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/publishers/$pubId" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "publisher detail" ($pubDetail.modules.Count -ge 1) "publisher=$pubId modules=$($pubDetail.modules.Count)"
} catch {
    Add-Check "publisher detail" $false $_.Exception.Message
}

try {
    $security = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/security" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "security center" ($security.metadata_health -eq "healthy") "health=$($security.metadata_health)"
} catch {
    Add-Check "security center" $false $_.Exception.Message
}

try {
    $preflight = Invoke-RestMethod -Uri "$BaseUrl/api/modules/store/integration.heartbeat/1.0.0/preflight" -Headers $headers -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec $TimeoutSec
    Add-Check "preflight readonly" ($preflight.policy.decision -eq "ALLOW") "decision=$($preflight.policy.decision)"
} catch {
    Add-Check "preflight readonly" $false $_.Exception.Message
}

try {
    $runtime = Invoke-RestMethod -Uri "$BaseUrl/api/modules/runtime" -Headers $headers -TimeoutSec $TimeoutSec
    Add-Check "runtime blocked flag" ($runtime.runtime_blocked -eq $true) "blocked=$($runtime.runtime_blocked)"
} catch {
    Add-Check "runtime blocked flag" $false $_.Exception.Message
}

try {
    $dash = Invoke-WebRequest -Uri "$BaseUrl/" -TimeoutSec $TimeoutSec -UseBasicParsing
    Add-Check "core dashboard" ($dash.StatusCode -eq 200) "status=$($dash.StatusCode)"
} catch {
    Add-Check "core dashboard" $false $_.Exception.Message
}

Write-Host ""
foreach ($c in $checks) {
    $mark = if ($c.Ok) { "[OK]" } else { "[FAIL]" }
    Write-Host "$mark $($c.Name): $($c.Detail)"
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host ("Store acceptance FAILED: {0} check(s)" -f $failures.Count)
    exit 1
}

Write-Host ""
Write-Host "Store acceptance PASSED"
exit 0
