$ErrorActionPreference = "SilentlyContinue"

$patterns = @(
    "1komma5",
    "uvicorn",
    "next dev",
    "vitest",
    "npm-cli.js run dev",
    "npm-cli.js run test",
    "npx-cli.js vitest",
    "python -m app"
)

function Matches-DevProcess([string]$commandLine) {
    if (-not $commandLine) { return $false }
    foreach ($pattern in $patterns) {
        if ($commandLine -like "*$pattern*") { return $true }
    }
    return $false
}

$stopped = @()

foreach ($proc in Get-CimInstance Win32_Process) {
    if ($proc.Name -notin @("node.exe", "python.exe", "python3.exe", "uv.exe")) { continue }
    if (-not (Matches-DevProcess $proc.CommandLine)) { continue }
    Write-Host "Stopping $($proc.ProcessId) $($proc.Name)"
    Stop-Process -Id $proc.ProcessId -Force
    $stopped += $proc.ProcessId
}

foreach ($proc in Get-CimInstance Win32_Process) {
    if ($proc.Name -ne "powershell.exe") { continue }
    $cmd = $proc.CommandLine
    if ($cmd -notlike "*1komma5*") { continue }
    if ($cmd -notlike "*npm run*" -and $cmd -notlike "*vitest*" -and $cmd -notlike "*uvicorn*" -and $cmd -notlike "*next dev*" -and $cmd -notlike "*collector*") {
        continue
    }
    Write-Host "Stopping shell $($proc.ProcessId)"
    Stop-Process -Id $proc.ProcessId -Force
    $stopped += $proc.ProcessId
}

Write-Host "Stopped $($stopped.Count) process(es)."

$listening = netstat -ano | Select-String "LISTENING" | Select-String ":3000 |:8000 |:5432 "
if ($listening) {
    Write-Host "Still listening:"
    $listening
} else {
    Write-Host "Ports 3000, 8000, 5432 are free."
}
