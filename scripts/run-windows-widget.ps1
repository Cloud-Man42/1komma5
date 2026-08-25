# Start EMIC Windows taskbar widget.
# Run from repo root: .\scripts\run-windows-widget.ps1
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$windowsDir = Join-Path $repoRoot "windows"
$project = Join-Path $windowsDir "EMIC.Tray\EMIC.Tray.csproj"

if (-not (Test-Path $project)) {
    throw "Project not found: $project"
}

Write-Host "Starting EMIC Windows widget from $windowsDir"
Push-Location $windowsDir
try {
    dotnet run --project EMIC.Tray\EMIC.Tray.csproj
} finally {
    Pop-Location
}
