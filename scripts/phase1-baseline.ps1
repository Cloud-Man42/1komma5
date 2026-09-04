param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [int[]]$Concurrency = @(1, 5, 10)
)

$ErrorActionPreference = "Stop"
$routes = @(
    "/api/sites/$Site/snapshot",
    "/api/sites/$Site/dashboard",
    "/api/sites/$Site/readings?bucket=5&hours=24",
    "/api/sites/$Site/solar/forecast",
    "/api/sites/$Site/price-engine/current",
    "/api/sites/$Site/battery-opportunity",
    "/api/sites/$Site/horizon-optimizer",
    "/api/sites/$Site/financial-stats?period=day",
    "/api/sites/$Site/financial-stats?period=month",
    "/api/sites/$Site/financial-stats?period=year",
    "/api/sites"
)

Write-Host "EMIC Phase 1 baseline against $BaseUrl (site=$Site)"
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
        $sorted = $rows.Ms | Sort-Object
        $p95Index = [math]::Max(0, [math]::Ceiling($sorted.Count * 0.95) - 1)
        $p95 = [math]::Round($sorted[$p95Index], 1)
        Write-Host ("  {0} users: ok={1}/{0} avg={2}ms p95={3}ms" -f $users, $ok, $avg, $p95)
        $results += [PSCustomObject]@{ Route = $route; Users = $users; Ok = $ok; AvgMs = $avg; P95Ms = $p95 }
    }
}

$outDir = Join-Path $PSScriptRoot "..\docs\emic-analysis\phase1"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$out = Join-Path $outDir "baseline-prod-results.json"
$results | ConvertTo-Json | Set-Content -Encoding utf8 $out
Write-Host "`nWrote $($results.Count) rows to $out"
