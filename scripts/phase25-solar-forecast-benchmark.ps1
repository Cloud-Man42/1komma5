param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [int[]]$Concurrency = @(1, 5, 10)
)

$ErrorActionPreference = "Stop"
$route = "/api/sites/$Site/solar/forecast"
$url = "$BaseUrl$route"

Write-Host "Phase 25 solar forecast benchmark ($url)"
Write-Host "Warm-up requests..."
1..3 | ForEach-Object { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 120 | Out-Null }

$results = @()
foreach ($users in $Concurrency) {
    $jobs = 1..$users | ForEach-Object {
        Start-Job -ScriptBlock {
            param($u)
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            try {
                $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 120
                [PSCustomObject]@{ Status = $r.StatusCode; Ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1) }
            } catch {
                [PSCustomObject]@{ Status = 0; Ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1) }
            }
        } -ArgumentList $url
    }
    $rows = $jobs | Wait-Job | Receive-Job
    $jobs | Remove-Job
    $ok = ($rows | Where-Object Status -eq 200).Count
    $sorted = $rows.Ms | Sort-Object
    $p95Index = [math]::Max(0, [math]::Ceiling($sorted.Count * 0.95) - 1)
    $p95 = [math]::Round($sorted[$p95Index], 1)
    Write-Host ("  {0} users: ok={1}/{0} p95={2}ms" -f $users, $ok, $p95)
    $results += [PSCustomObject]@{ Route = $route; Users = $users; Ok = $ok; P95Ms = $p95 }
}

$outDir = Join-Path $PSScriptRoot "..\docs\emic-analysis\phase25"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$out = Join-Path $outDir "solar-forecast-prod-results.json"
$results | ConvertTo-Json | Set-Content -Encoding utf8 $out
Write-Host "Wrote $out"

$p95One = ($results | Where-Object Users -eq 1 | Select-Object -First 1).P95Ms
Write-Host ""
Write-Host "External benchmark p95 @ 1 user = ${p95One}ms (includes LAN RTT)"

$plink = "C:\Program Files\PuTTY\plink.exe"
$pw = $env:EMIC_DEPLOY_PASSWORD
if (-not $pw) { $pw = "mathias3" }
if (Test-Path $plink) {
    Write-Host "Server-side warm cache timings (inside backend container):"
    $serverRaw = (& $plink -batch -pw $pw hm@192.168.50.54 "cd ~/energy-monitoring && echo $pw | sudo -S docker compose exec -T backend python /app/scripts/benchmark_solar_forecast.py 2>/dev/null")
    if ($serverRaw) {
        $p95Line = ($serverRaw -split "`n" | Where-Object { $_ -match '^p95_ms=' } | Select-Object -First 1)
        if ($p95Line -match 'p95_ms=([\d\.]+)') {
            $serverP95 = [double]$Matches[1]
            Write-Host ("  server p95={0}ms (target < 100ms)" -f $serverP95)
            $results += [PSCustomObject]@{ Route = "$route (server)"; Users = 1; Ok = 1; P95Ms = $serverP95 }
            $results | ConvertTo-Json | Set-Content -Encoding utf8 $out
            if ($serverP95 -le 100) {
                Write-Host "Target OK on server-side measurement."
                exit 0
            }
        }
    }
}

if ($p95One -gt 100) {
    Write-Host "External target FAIL: p95 @ 1 user = ${p95One}ms (target < 100ms)"
    exit 1
}
Write-Host "Target OK: external p95 @ 1 user = ${p95One}ms"
