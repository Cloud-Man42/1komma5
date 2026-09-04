param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [string]$DisplayToken = $env:EMIC_DISPLAY_TOKEN,
    [int[]]$Concurrency = @(1, 5)
)

$ErrorActionPreference = "Stop"

$routes = @(
    @{ Route = "/api/sites/$Site/dashboard"; Auth = $false; Note = "Pi data proxy" },
    @{ Route = "/api/v1/display/overview/$Site"; Auth = $true; Note = "Pi overview" },
    @{ Route = "/api/v1/display/overview/$Site/stream"; Auth = $true; Note = "Pi SSE (HEAD)" }
)

Write-Host "Phase 20 Pi baseline on $BaseUrl site=$Site"
$results = @()

foreach ($entry in $routes) {
    $url = "$BaseUrl$($entry.Route)"
    Write-Host "`n== $($entry.Route) ($($entry.Note)) =="
    if ($entry.Auth -and -not $DisplayToken) {
        Write-Host "  SKIP (set EMIC_DISPLAY_TOKEN for authenticated Pi routes)"
        $results += [PSCustomObject]@{
            Route = $entry.Route
            Users = 0
            Ok = 0
            AvgMs = $null
            P95Ms = $null
            Skipped = $true
        }
        continue
    }

    $headers = @{}
    if ($entry.Auth) {
        $headers["Authorization"] = "Bearer $DisplayToken"
    }

    foreach ($users in $Concurrency) {
        if ($entry.Route -like "*/stream") {
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            try {
                $res = Invoke-WebRequest -Uri $url -Method Head -Headers $headers -UseBasicParsing -TimeoutSec 30
                $ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1)
                $ok = if ($res.StatusCode -eq 200) { 1 } else { 0 }
                Write-Host ("  HEAD: ok={0}/1 {1}ms content-type={2}" -f $ok, $ms, $res.Headers["Content-Type"])
                $results += [PSCustomObject]@{ Route = $entry.Route; Users = 1; Ok = $ok; AvgMs = $ms; P95Ms = $ms; Skipped = $false }
            } catch {
                Write-Host "  HEAD FAIL: $($_.Exception.Message)"
                $results += [PSCustomObject]@{ Route = $entry.Route; Users = 1; Ok = 0; AvgMs = $null; P95Ms = $null; Skipped = $false }
            }
            break
        }

        $jobs = 1..$users | ForEach-Object {
            Start-Job -ScriptBlock {
                param($u, $h)
                $sw = [System.Diagnostics.Stopwatch]::StartNew()
                try {
                    $params = @{ Uri = $u; UseBasicParsing = $true; TimeoutSec = 120 }
                    if ($h.Count -gt 0) { $params.Headers = $h }
                    $r = Invoke-WebRequest @params
                    [PSCustomObject]@{
                        Status = $r.StatusCode
                        Ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1)
                    }
                } catch {
                    [PSCustomObject]@{ Status = 0; Ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1) }
                }
            } -ArgumentList $url, $headers
        }
        $rows = $jobs | Wait-Job | Receive-Job
        $jobs | Remove-Job
        $ok = ($rows | Where-Object Status -eq 200).Count
        $avg = [math]::Round(($rows.Ms | Measure-Object -Average).Average, 1)
        $sorted = $rows.Ms | Sort-Object
        $p95Index = [math]::Max(0, [math]::Ceiling($sorted.Count * 0.95) - 1)
        $p95 = [math]::Round($sorted[$p95Index], 1)
        Write-Host ("  {0} users: ok={1}/{0} avg={2}ms p95={3}ms" -f $users, $ok, $avg, $p95)
        $results += [PSCustomObject]@{ Route = $entry.Route; Users = $users; Ok = $ok; AvgMs = $avg; P95Ms = $p95; Skipped = $false }
    }
}

$outDir = Join-Path $PSScriptRoot "..\docs\emic-analysis\phase1"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$out = Join-Path $outDir "pi-baseline-prod-results.json"
$results | ConvertTo-Json | Set-Content -Encoding utf8 $out
Write-Host "`nWrote $($results.Count) rows to $out"
