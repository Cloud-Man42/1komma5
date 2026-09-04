param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [int]$PollSeconds = 120,
    [int]$MaxWaitMinutes = 720,
    [switch]$WaitForEv,
    [switch]$SkipApply,
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN
)

$ErrorActionPreference = "Stop"

function Get-AdminToken {
    param([string]$Token)
    if ($Token) { return $Token.Trim() }
    $plink = "C:\Program Files\PuTTY\plink.exe"
    $pw = $env:EMIC_DEPLOY_PASSWORD
    if ($pw -and (Test-Path $plink)) {
        return (& $plink -batch -pw $pw hm@192.168.50.54 "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
    }
    throw "EMIC_ADMIN_TOKEN required"
}

function Test-EvReady {
    param($Bridge, [array]$Mappings, $Discovery)
    foreach ($m in $Mappings) {
        if ($m.heartbeat_ev_id) { return $true }
    }
    if ($Bridge.ev_id) { return $true }
    if ($Discovery -and $Discovery.resolved_ev_id) { return $true }
    return $false
}

$AdminToken = Get-AdminToken $AdminToken
$headers = @{
    Authorization = "Bearer $AdminToken"
    "Content-Type"  = "application/json"
}

Write-Host "Phase 22 Heartbeat control activate ($Site @ $BaseUrl)"

$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
$discovery = $null
while ($true) {
    $bridge = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/status" -Headers $headers
    $mappings = @(Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/mappings" -Headers $headers)

    if (-not (Test-EvReady $bridge $mappings $discovery)) {
        Write-Host ("[{0}] EV not ready (class={1}, mappings={2}). Running discovery..." -f (Get-Date -Format "HH:mm:ss"), $bridge.setup_classification, $mappings.Count)
        $discovery = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/discovery/run" -Method Post -Headers $headers
        Write-Host ("  discovery class={0} resolved_ev_id={1}" -f $discovery.setup_classification, $discovery.resolved_ev_id)
        $bridge = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/status" -Headers $headers
        $mappings = @(Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/mappings" -Headers $headers)
    }

    if (Test-EvReady $bridge $mappings $discovery) {
        Write-Host "EV ready (class=$($bridge.setup_classification), mappings=$($mappings.Count), ev_id=$($bridge.ev_id))"
        break
    }

    if (-not $WaitForEv) {
        Write-Host "EV not ready. Re-run with -WaitForEv to poll until Heartbeat registers the vehicle."
        exit 2
    }
    if ((Get-Date) -ge $deadline) {
        Write-Host "Timed out after $MaxWaitMinutes minutes waiting for Heartbeat EV."
        exit 3
    }
    Write-Host ("Waiting ${PollSeconds}s before next check...")
    Start-Sleep -Seconds $PollSeconds
}

Write-Host ""
Write-Host "Step 3a - dry-run write test"
$dryTest = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/write-test/run?dry_run=true" -Method Post -Headers $headers
Write-Host ("  classification={0}" -f $dryTest.classification)
if ($dryTest.classification -ne "DRY_RUN") {
    Write-Warning "Dry-run write test did not return DRY_RUN: $($dryTest.error)"
    exit 4
}

Write-Host "Step 3b - enable write_enabled"
$settings = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/heartbeat/bridge/settings" -Method Patch -Headers $headers -Body '{"write_enabled": true}'
Write-Host ("  write_enabled={0}" -f $settings.write_enabled)

Write-Host ""
Write-Host "Step 4a - energy control preview"
$previewBody = @{ action = "USE_NOW"; target = "ev_charger" } | ConvertTo-Json
$preview = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/preview" -Method Post -Headers $headers -Body $previewBody
Write-Host ("  outcome={0} reason={1}" -f $preview.outcome, $preview.reason_sv)
if ($preview.outcome -ne "PREVIEW") {
    Write-Warning "Preview not PREVIEW. Check mapping confidence vs threshold."
    exit 5
}

if (-not $SkipApply) {
    Write-Host "Step 4b - manual apply (requires EV plugged in at Heartbeat)"
    $apply = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$Site/energy-control/apply" -Method Post -Headers $headers -Body $previewBody
    Write-Host ("  outcome={0} reason={1}" -f $apply.outcome, $apply.reason_sv)
    if ($apply.outcome -ne "APPLIED") {
        Write-Warning "Apply was not APPLIED (may be OK if EV offline). Re-run apply when charging."
    }
}

Write-Host ""
Write-Host "Running AUTOMATIC readiness check..."
& (Join-Path $PSScriptRoot "phase22-automatic-readiness.ps1") -BaseUrl $BaseUrl -Site $Site -AdminToken $AdminToken
exit $LASTEXITCODE
