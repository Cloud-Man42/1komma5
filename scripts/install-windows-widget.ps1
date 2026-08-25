# Install EMIC Windows taskbar widget to %LOCALAPPDATA%\Programs\EMIC
# Run from repo root: .\scripts\install-windows-widget.ps1
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "publish-windows-widget.ps1")

$sourceDir = Join-Path $repoRoot "windows\EMIC.Tray\bin\Release\net8.0-windows\win-x64\publish"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\EMIC"
$stagingDir = Join-Path $env:TEMP ("emic-install-" + [guid]::NewGuid().ToString("n"))

function Stop-EmicProcesses {
    $procs = @(Get-Process -Name "EMIC" -ErrorAction SilentlyContinue)
    if ($procs.Count -eq 0) {
        return $true
    }

    Write-Host "Stopping running EMIC instance(s)..."
    foreach ($proc in $procs) {
        try {
            if (-not $proc.CloseMainWindow()) {
                $null = $proc.WaitForExit(3000)
            }
        } catch {
            # tray apps may not have a main window
        }
    }

    Start-Sleep -Seconds 1
    $ErrorActionPreference = "SilentlyContinue"
    cmd /c "taskkill /F /IM EMIC.exe" | Out-Null
    $ErrorActionPreference = "Stop"
    Start-Sleep -Seconds 2
    return -not (Get-Process -Name "EMIC" -ErrorAction SilentlyContinue)
}

function Install-ToDirectory {
    param(
        [string]$TargetDir
    )

    if (Test-Path $stagingDir) {
        Remove-Item $stagingDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null
    Copy-Item -Path (Join-Path $sourceDir "*") -Destination $stagingDir -Recurse -Force

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    Copy-Item -Path (Join-Path $stagingDir "*") -Destination $TargetDir -Recurse -Force
}

$stopped = Stop-EmicProcesses
$targetDir = $installDir
$usedFallback = $false

try {
    Write-Host "Installing to $installDir ..."
    Install-ToDirectory -TargetDir $installDir
} catch [System.IO.IOException] {
    if (-not $stopped) {
        $targetDir = "$installDir.new"
        $usedFallback = $true
        Write-Host ""
        Write-Host "Could not overwrite running install (files locked)."
        Write-Host "Installing fresh copy to $targetDir instead ..."
        Install-ToDirectory -TargetDir $targetDir
    } else {
        throw
    }
} finally {
    if (Test-Path $stagingDir) {
        Remove-Item $stagingDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$exePath = Join-Path $targetDir "EMIC.exe"
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$wsh = New-Object -ComObject WScript.Shell

foreach ($pair in @(
        @{ Dir = $startMenuDir; Name = "EMIC Widget.lnk" },
        @{ Dir = $startupDir; Name = "EMIC Widget.lnk" }
    )) {
    $shortcutPath = Join-Path $pair.Dir $pair.Name
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = $targetDir
    $shortcut.Description = "EMIC energi-widget i taskbar"
    $shortcut.Save()
    Write-Host "Created shortcut: $shortcutPath"
}

Start-Process -FilePath $exePath -WorkingDirectory $targetDir

Write-Host ""
Write-Host "EMIC installed and started."
Write-Host "Look for the green icon near the clock (^ overflow if hidden)."
Write-Host "Exe: $exePath"
if ($usedFallback) {
    Write-Host ""
    Write-Host "Tip: Hogerklicka gammal EMIC-ikon vid klockan -> Avsluta."
    Write-Host "     Du kan sedan ta bort $installDir om du vill."
}
