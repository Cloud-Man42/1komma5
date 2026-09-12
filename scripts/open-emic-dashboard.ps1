#!/usr/bin/env pwsh
# Open EMIC dashboard and auto-save admin token for this browser session.
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://emic.inacloud.se" })
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/lib/Get-EmicDeployCredential.ps1"

$token = Get-EmicAdminTokenLocal
if (-not $token) {
    $token = Get-EmicAdminTokenFromRemote
    $tokenFile = Join-Path $env:USERPROFILE ".emic-admin-token"
    Set-Content -Path $tokenFile -Value $token -NoNewline
}

$url = "$($BaseUrl.TrimEnd('/'))/?emic_setup_token=$token"
Write-Host "Opening dashboard with one-shot token setup..."
Start-Process $url
