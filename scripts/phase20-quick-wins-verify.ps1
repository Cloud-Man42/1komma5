param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp"
)

$ErrorActionPreference = "Stop"

$checks = @(
    @{ Name = "integration-health"; Url = "/api/sites/$Site/integration-health" },
    @{ Name = "dashboard"; Url = "/api/sites/$Site/dashboard" },
    @{ Name = "battery-opportunity"; Url = "/api/sites/$Site/battery-opportunity" },
    @{ Name = "horizon-optimizer"; Url = "/api/sites/$Site/horizon-optimizer" },
    @{ Name = "energy-control-status"; Url = "/api/sites/$Site/energy-control/status" },
    @{ Name = "financial-stats-day"; Url = "/api/sites/$Site/financial-stats?period=day" }
)

Write-Host "Phase 20 quick wins verify on $BaseUrl site=$Site"
$failed = 0

foreach ($check in $checks) {
    $url = "$BaseUrl$($check.Url)"
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $res = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 120
        $ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 0)
        if ($res.StatusCode -ne 200) {
            Write-Host "  FAIL $($check.Name): HTTP $($res.StatusCode)"
            $failed++
            continue
        }
        Write-Host ("  OK   {0} ({1}ms)" -f $check.Name, $ms)
    } catch {
        Write-Host "  FAIL $($check.Name): $($_.Exception.Message)"
        $failed++
    }
}

if ($failed -gt 0) {
    throw "$failed quick-win check(s) failed"
}

Write-Host "All quick-win endpoints OK."
