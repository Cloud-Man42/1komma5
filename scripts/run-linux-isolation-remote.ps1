# Run Linux isolation suite on production-equivalent remote host (Sprint C.6).
param(
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$KeyFile = $env:EMIC_DEPLOY_KEY,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE,
    [string]$RemoteDir = "energy-monitoring"
)

$ErrorActionPreference = "Stop"
if (-not $Server) { $Server = "192.168.50.54" }
if (-not $User) { $User = "hm" }

$plink = "C:\Program Files\PuTTY\plink.exe"
if (-not (Test-Path $plink)) { throw "PuTTY plink not found" }

if ($PasswordFile) {
    if (-not (Test-Path $PasswordFile)) { throw "Password file not found: $PasswordFile" }
    $Password = (Get-Content -Path $PasswordFile -Raw).Trim()
}
$authArgs = @("-batch")
if ($KeyFile) {
    $authArgs += @("-i", $KeyFile)
} elseif ($Password) {
    $authArgs += @("-pw", $Password)
} else {
    throw "Deploy credentials required"
}

function Invoke-Plink([string]$Command) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = (& $plink @authArgs "${User}@${Server}" $Command 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $prev
    return $out
}

$pscp = "C:\Program Files\PuTTY\pscp.exe"
$repoRoot = Split-Path -Parent $PSScriptRoot
Write-Host "Uploading Linux isolation test assets..."
Invoke-Plink "mkdir -p ~/energy-monitoring/packages/energy-core/tests/platform ~/energy-monitoring/packages/energy-core/tests/fixtures ~/energy-monitoring/modules" | Out-Null
& $pscp @authArgs -r "$repoRoot\packages\energy-core\tests\platform\isolation" "${User}@${Server}:energy-monitoring/packages/energy-core/tests/platform/" | Out-Null
& $pscp @authArgs -r "$repoRoot\packages\energy-core\tests\fixtures\modules" "${User}@${Server}:energy-monitoring/packages/energy-core/tests/fixtures/" | Out-Null
& $pscp @authArgs "$repoRoot\packages\energy-core\tests\isolation_linux_helpers.py" "${User}@${Server}:energy-monitoring/packages/energy-core/tests/" | Out-Null
& $pscp @authArgs "$repoRoot\scripts\run-linux-isolation-suite.sh" "${User}@${Server}:energy-monitoring/scripts/" | Out-Null
& $pscp @authArgs "$repoRoot\scripts\sign_sensibo_package.py" "${User}@${Server}:energy-monitoring/scripts/" | Out-Null
if (Test-Path "$repoRoot\modules\sensibo") {
    & $pscp @authArgs -r "$repoRoot\modules\sensibo" "${User}@${Server}:energy-monitoring/modules/" | Out-Null
}

Write-Host "== Linux isolation suite on ${Server} =="
Invoke-Plink "cd ~/$RemoteDir && sed -i 's/\r$//' scripts/run-linux-isolation-suite.sh && chmod +x scripts/run-linux-isolation-suite.sh" | Out-Null

if ($SudoPasswordFile -and (Test-Path $SudoPasswordFile)) {
    & $pscp @authArgs $SudoPasswordFile "${User}@${Server}:.emic-deploy-sudo" | Out-Null
    Invoke-Plink "chmod 600 ~/.emic-deploy-sudo" | Out-Null
    $remoteCmd = "cd ~/$RemoteDir && sudo -S bash scripts/run-linux-isolation-suite.sh < ~/.emic-deploy-sudo; rm -f ~/.emic-deploy-sudo"
} elseif ($Password) {
    $remoteCmd = "cd ~/$RemoteDir && echo '$Password' | sudo -S bash scripts/run-linux-isolation-suite.sh"
} else {
    $remoteCmd = "cd ~/$RemoteDir && bash scripts/run-linux-isolation-suite.sh"
}

$result = Invoke-Plink $remoteCmd
Write-Host $result
if ($result -match "SENSIBO E2E SUMMARY:") {
    if ($result -match "(\d+) failed" -and [int]$Matches[1] -gt 0) {
        Write-Host "Linux Sensibo E2E FAILED ($($Matches[1]) failed)"
        exit 1
    }
    if ($result -match "(\d+) skipped" -and [int]$Matches[1] -gt 0) {
        Write-Host "Linux Sensibo E2E FAILED ($($Matches[1]) skipped)"
        exit 1
    }
    Write-Host "Linux Sensibo E2E PASSED"
    exit 0
}
if ($result -match "LINUX ISOLATION SUMMARY:") {
    if ($result -match "(\d+) failed" -and [int]$Matches[1] -gt 0) {
        Write-Host "Linux isolation suite FAILED"
        exit 1
    }
    if ($result -match "(\d+) skipped" -and [int]$Matches[1] -gt 0) {
        Write-Host "Linux isolation suite FAILED (skipped)"
        exit 1
    }
    Write-Host "Linux isolation suite PASSED"
    exit 0
}
Write-Host "Linux isolation suite did not complete successfully"
exit 1
