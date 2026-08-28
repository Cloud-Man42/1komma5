param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Site = "akarp",
    [int[]]$Concurrency = @(1, 5, 10)
)

$ErrorActionPreference = "Stop"
$routes = @(
    "/api/sites/$Site/snapshot",
    "/api/sites/$Site/dashboard",
    "/api/sites/$Site/readings?bucket=5&hours=24",
    "/api/sites/$Site/solar/forecast"
)

Write-Host "EMIC performance baseline against $BaseUrl"
$results = @()

foreach ($route in $routes) {
    $url = "$BaseUrl$route"
    Write-Host "`n== $route =="
    foreach ($users in $Concurrency) {
        $jobs = 1..$users | ForEach-Object {
            Start-Job -ScriptBlock {
                param($u)
                $sw = [System.Diagnostics.Stopwatch]::StartNew()
                try {
                    $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 120
                    [PSCustomObject]@{
                        Status = $r.StatusCode
                        Ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1)
                        Bytes = $r.RawContentLength
                    }
                } catch {
                    [PSCustomObject]@{ Status = 0; Ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1); Bytes = 0 }
                }
            } -ArgumentList $url
        }
        $rows = $jobs | Wait-Job | Receive-Job
        $jobs | Remove-Job
        $ok = ($rows | Where-Object Status -eq 200).Count
        $avg = [math]::Round(($rows.Ms | Measure-Object -Average).Average, 1)
        $p95 = [math]::Round(($rows.Ms | Sort-Object)[[math]::Ceiling($rows.Count * 0.95) - 1], 1)
        Write-Host ("  {0} users: ok={1}/{0} avg={2}ms p95={3}ms" -f $users, $ok, $avg, $p95)
        $results += [PSCustomObject]@{ Route = $route; Users = $users; Ok = $ok; AvgMs = $avg; P95Ms = $p95 }
    }
}

$out = Join-Path $PSScriptRoot "..\docs\performance\baseline-results.json"
$results | ConvertTo-Json | Set-Content -Encoding utf8 $out
Write-Host "`nWrote $($results.Count) rows to $out"
