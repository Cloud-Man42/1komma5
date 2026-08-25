# Windows test runner for energy monitoring monorepo
$ErrorActionPreference = "Stop"

$uv = "$env:USERPROFILE\.local\bin\uv.exe"
if (-not (Test-Path $uv)) {
    $uv = "uv"
}

Write-Host "Running Python tests..."
& $uv run --all-packages pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running Windows client tests..."
Push-Location windows
dotnet test --nologo
$windowsExit = $LASTEXITCODE
Pop-Location
if ($windowsExit -ne 0) { exit $windowsExit }

Write-Host "Running frontend tests..."
Push-Location frontend
npm test
$frontendExit = $LASTEXITCODE
Pop-Location
exit $frontendExit
