# Publish EMIC Windows taskbar widget as a standalone exe folder.
# Run from repo root: .\scripts\publish-windows-widget.ps1
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$windowsDir = Join-Path $repoRoot "windows"
$project = Join-Path $windowsDir "EMIC.Tray\EMIC.Tray.csproj"

if (-not (Test-Path $project)) {
    throw "Project not found: $project"
}

Push-Location $windowsDir
try {
    dotnet publish EMIC.Tray\EMIC.Tray.csproj -c Release -r win-x64 --self-contained false
} finally {
    Pop-Location
}

$publishDir = Join-Path $windowsDir "EMIC.Tray\bin\Release\net8.0-windows\win-x64\publish"
Write-Host ""
Write-Host "Published to:"
Write-Host "  $publishDir\EMIC.exe"
