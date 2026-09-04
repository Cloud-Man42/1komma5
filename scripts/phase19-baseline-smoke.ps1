param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp"
)

$ErrorActionPreference = "Stop"
$routes = @(
    "/health",
    "/api/sites/$Site/dashboard",
    "/api/sites/$Site/price-engine/current",
    "/api/sites/$Site/solar/forecast",
    "/api/sites/$Site/battery-opportunity",
    "/api/sites/$Site/horizon-optimizer"
)

Write-Host "Phase 19 baseline smoke against $BaseUrl"
$failed = 0
foreach ($route in $routes) {
    $url = "$BaseUrl$route"
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60
        $status = $response.StatusCode
    } catch {
        $status = 0
    }
    if ($status -ne 200) {
        $failed += 1
        Write-Host "FAIL $route -> $status"
    } else {
        Write-Host "OK   $route"
    }
}

if ($failed -gt 0) {
    throw "$failed route(s) failed smoke check"
}

Write-Host "All $($routes.Count) routes returned 200"
