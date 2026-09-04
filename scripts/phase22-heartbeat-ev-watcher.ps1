param(
    [int]$PollSeconds = 300,
    [int]$MaxWaitMinutes = 720
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Heartbeat EV watcher - polls every ${PollSeconds}s (max ${MaxWaitMinutes}m)"
Write-Host "Register EQE in Heartbeat app, then this script completes steps 3-4 automatically."
Write-Host ""

& (Join-Path $PSScriptRoot "phase22-heartbeat-control-activate.ps1") `
    -WaitForEv `
    -PollSeconds $PollSeconds `
    -MaxWaitMinutes $MaxWaitMinutes

exit $LASTEXITCODE
