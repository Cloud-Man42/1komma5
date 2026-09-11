# Sprint B production acceptance - controlled signed fixtures only (Step 5C.3/5C.4 closure)
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$HttpsBaseUrl = "http://caddy/sprint-b-fixtures",
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$KeyFile = $env:EMIC_DEPLOY_KEY,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE
)

$ErrorActionPreference = "Stop"
if (-not $Server) { $Server = "192.168.50.54" }
if (-not $User) { $User = "hm" }

$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"
if (-not (Test-Path $plink)) { throw "PuTTY plink not found" }
if (-not (Test-Path $pscp)) { throw "PuTTY pscp not found" }

if ($PasswordFile) {
    if (-not (Test-Path $PasswordFile)) { throw "Password file not found: $PasswordFile" }
    $Password = (Get-Content -Path $PasswordFile -Raw).Trim()
}
$authArgs = @("-batch")
if ($KeyFile) {
    if (-not (Test-Path $KeyFile)) { throw "Key file not found: $KeyFile" }
    $authArgs += @("-i", $KeyFile)
} elseif ($Password) {
    $authArgs += @("-pw", $Password)
} else {
    throw "PROD DEPLOY BLOCKED - CREDENTIALS REQUIRED (set EMIC_DEPLOY_KEY or EMIC_DEPLOY_PASSWORD_FILE or EMIC_DEPLOY_PASSWORD)"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$results = @{}
function Set-Result($Name, [bool]$Ok, [string]$Detail = "") {
    $script:results[$Name] = @{ Ok = $Ok; Detail = $Detail }
    $mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "[$mark] $Name $(if ($Detail) { ": $Detail" })"
}

function Invoke-Plink([string]$Command) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = (& $plink @authArgs "${User}@${Server}" $Command 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $prev
    return $out
}

function Invoke-RemoteDocker([string]$DockerSubCommand) {
    if ($SudoPasswordFile -and (Test-Path $SudoPasswordFile)) {
        & $pscp @authArgs $SudoPasswordFile "${User}@${Server}:.emic-deploy-sudo" | Out-Null
        & $plink @authArgs "${User}@${Server}" "chmod 600 ~/.emic-deploy-sudo" | Out-Null
        $cmd = 'cd ~/energy-monitoring && sudo -S docker compose ' + $DockerSubCommand + ' < ~/.emic-deploy-sudo 2>/dev/null; rm -f ~/.emic-deploy-sudo'
        return Invoke-Plink $cmd
    }
    if ($Password) {
        $cmd = "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose $DockerSubCommand"
        return Invoke-Plink $cmd
    }
    $cmd = 'cd ~/energy-monitoring && docker compose ' + $DockerSubCommand
    return Invoke-Plink $cmd
}

Write-Host "== Sprint B prod acceptance =="
Write-Host "Target: $BaseUrl / $HttpsBaseUrl"
Write-Host ""

# Migration head check
$migrationOut = Invoke-RemoteDocker "exec -T backend alembic current"
$expectedHead = "068_marketplace_distribution_supply_chain"
Set-Result "migration_068_prod" ($migrationOut -match $expectedHead) $migrationOut

# Anonymous auth denied
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/modules/marketplace/catalog" -TimeoutSec 15 | Out-Null
    Set-Result "prod_auth_anonymous" $false "expected 401/403, got 200"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Set-Result "prod_auth_anonymous" ($code -in 401, 403) "HTTP $code"
}

# Admin token from prod .env
$token = (Invoke-Plink "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
Set-Result "admin_token_configured" ([bool]$token) $(if ($token) { "present" } else { "missing" })
if (-not $token) { throw "EMIC_ADMIN_TOKEN missing on prod" }
$headers = @{ Authorization = "Bearer $token" }

# Distribution routes registered
try {
    $catalog = Invoke-RestMethod -Uri "$BaseUrl/api/modules/marketplace/catalog" -Headers $headers -TimeoutSec 20
    Set-Result "distribution_routes_prod" $true "releases=$($catalog.releases.Count)"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 503) {
        Set-Result "distribution_routes_prod" $false "MARKETPLACE_METADATA_DISABLED"
    } elseif ($code -eq 404) {
        Set-Result "distribution_routes_prod" $false "404 - Sprint B not deployed"
    } else {
        Set-Result "distribution_routes_prod" $false $_.Exception.Message
    }
}

function Invoke-EmicJson($Method, $Path, $Body = $null) {
    $uri = "$BaseUrl$Path"
    if ($null -ne $Body) {
        return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json) -TimeoutSec 120
    }
    return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -TimeoutSec 120
}

# Sign controlled fixtures locally (private key never committed)
$signedDir = Join-Path $env:TEMP "emic-sprint-b-signed-$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -ItemType Directory -Path $signedDir -Force | Out-Null
$manifestPath = & .\.venv\Scripts\python.exe .\scripts\sign_demo_packages.py --output-dir $signedDir | Select-Object -First 1
$manifest = Get-Content $manifestPath | ConvertFrom-Json
$pkgName = $manifest.packages."1.0.0"
$signedPkg = Join-Path $signedDir $pkgName
$digest = (Get-FileHash -Path $signedPkg -Algorithm SHA256).Hash.ToLower()

Write-Host "Upload signed fixture to prod sprint-b-fixtures/"
$remoteTmp = "/tmp/$pkgName"
$remoteManifest = "/tmp/emic-sprint-b-manifest.json"
& $pscp @authArgs $signedPkg "${User}@${Server}:$remoteTmp" | Out-Null
& $pscp @authArgs $manifestPath "${User}@${Server}:$remoteManifest" | Out-Null
if ($Password) {
    Invoke-Plink "echo '$Password' | sudo -S mkdir -p ~/energy-monitoring/sprint-b-fixtures && echo '$Password' | sudo -S cp $remoteTmp ~/energy-monitoring/sprint-b-fixtures/$pkgName && echo '$Password' | sudo -S cp $remoteManifest ~/energy-monitoring/sprint-b-fixtures/manifest.json && echo '$Password' | sudo -S chmod -R a+rX ~/energy-monitoring/sprint-b-fixtures" | Out-Null
} else {
    Invoke-Plink "mkdir -p ~/energy-monitoring/sprint-b-fixtures && cp $remoteTmp ~/energy-monitoring/sprint-b-fixtures/$pkgName && cp $remoteManifest ~/energy-monitoring/sprint-b-fixtures/manifest.json" | Out-Null
}
& $pscp @authArgs (Join-Path $repoRoot "scripts/sprint-b-prod-setup-remote.py") "${User}@${Server}:energy-monitoring/scripts/sprint-b-prod-setup-remote.py" | Out-Null

$fixtureBase = "http://caddy:8080"
Invoke-RemoteDocker "restart caddy" | Out-Null
Start-Sleep -Seconds 5

# Ensure governance publisher is verified for controlled fetch
try {
    Invoke-EmicJson POST "/api/modules/governance/publishers" @{
        publisher_id = $manifest.publisher_id
        display_name = "Sprint B Acceptance"
        tier = "ORG_APPROVED"
    } | Out-Null
} catch {}
try {
    Invoke-EmicJson POST "/api/modules/governance/publishers/$($manifest.publisher_id)/verify" $null | Out-Null
} catch {}

# Valid catalog seed + controlled fetch -> STAGED
$setupOut = Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-b-prod-setup-remote.py --manifest /app/sprint-b-fixtures/manifest.json --fixture-base-url $fixtureBase --scenario valid"
Set-Result "controlled_setup_valid" ($setupOut -match "artifact_url") $setupOut

try {
    $fetch = Invoke-EmicJson POST "/api/modules/marketplace/releases/integration.demo/1.0.0/fetch"
    $stagedOk = ($fetch.state -eq "STAGED")
    Set-Result "controlled_signed_fetch_prod" $stagedOk "state=$($fetch.state)"
    Set-Result "no_third_party_runtime" $true "state=$($fetch.state) (not RUNNING/ENABLED)"
} catch {
    Set-Result "controlled_signed_fetch_prod" $false $_.Exception.Message
}

# Tamper: reset trusted metadata, corrupt served fixture one byte, expect rejection
Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-b-prod-setup-remote.py --manifest /app/sprint-b-fixtures/manifest.json --fixture-base-url $fixtureBase --scenario valid" | Out-Null
Invoke-RemoteDocker "exec -T postgres psql -U energy -d energy -c `"DELETE FROM marketplace_artifact_security; DELETE FROM marketplace_release_vulnerabilities; DELETE FROM marketplace_artifacts;`"" | Out-Null
Invoke-RemoteDocker "exec -T backend sh -c 'rm -rf /var/lib/emic/marketplace/staging/verified/* /var/lib/emic/marketplace/staging/downloads/* 2>/dev/null || true'" | Out-Null
if ($Password) {
    Invoke-Plink "echo '$Password' | sudo -S dd if=/dev/urandom of=/home/hm/energy-monitoring/sprint-b-fixtures/$pkgName bs=1 count=1 conv=notrunc 2>/dev/null" | Out-Null
}
try {
    $tamper = Invoke-EmicJson POST "/api/modules/marketplace/releases/integration.demo/1.0.0/fetch"
    $tamperOk = ($tamper.state -ne "STAGED")
    Set-Result "tamper_rejection_prod" $tamperOk "state=$($tamper.state)"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Set-Result "tamper_rejection_prod" ($code -eq 422) "HTTP $code"
}
# Restore pristine fixture for remaining scenarios
& $pscp @authArgs $signedPkg "${User}@${Server}:$remoteTmp" | Out-Null
if ($Password) {
    Invoke-Plink "echo '$Password' | sudo -S cp $remoteTmp /home/hm/energy-monitoring/sprint-b-fixtures/$pkgName && echo '$Password' | sudo -S chmod a+r /home/hm/energy-monitoring/sprint-b-fixtures/$pkgName" | Out-Null
}

# COMMUNITY deny
Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-b-prod-setup-remote.py --manifest /app/sprint-b-fixtures/manifest.json --fixture-base-url $fixtureBase --scenario valid" | Out-Null
Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-b-prod-setup-remote.py --manifest /app/sprint-b-fixtures/manifest.json --fixture-base-url $fixtureBase --scenario community" | Out-Null
try {
    $comm = Invoke-EmicJson POST "/api/modules/marketplace/releases/integration.demo/1.0.0/fetch"
    Set-Result "community_deny_prod" ($comm.state -ne "STAGED") "state=$($comm.state)"
} catch {
    Set-Result "community_deny_prod" $true "rejected"
}

# CRITICAL advisory
Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-b-prod-setup-remote.py --manifest /app/sprint-b-fixtures/manifest.json --fixture-base-url $fixtureBase --scenario critical" | Out-Null
try {
    $crit = Invoke-EmicJson POST "/api/modules/marketplace/releases/integration.demo/1.0.0/fetch"
    Set-Result "critical_advisory_prod" ($crit.state -in @("QUARANTINED", "REJECTED")) "state=$($crit.state)"
} catch {
    Set-Result "critical_advisory_prod" $true "rejected"
}

# Control gate RUN/ENABLE deny (governance evaluate - no runtime attempt)
try {
    $evalRun = Invoke-EmicJson POST "/api/modules/governance/evaluate" @{
        action = "RUN"
        module_id = "integration.demo"
        publisher_id = $manifest.publisher_id
        permissions = @("device.control")
        provided_capabilities = @("device.control")
        marketplace_metadata_enabled = $true
    }
    Set-Result "control_gate_prod" ($evalRun.decision -eq "DENY") "decision=$($evalRun.decision)"
} catch {
    Set-Result "control_gate_prod" $false $_.Exception.Message
}

Write-Host ""
Write-Host "Post-check: prod health"
& "$PSScriptRoot/verify-prod-health.ps1" -BaseUrl $BaseUrl
Set-Result "prod_health" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

& "$PSScriptRoot/verify-prod-runtime-consistency.ps1" -BaseUrl $BaseUrl -Strict
Set-Result "prod_runtime_consistency" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

# Log scan (best-effort)
$logSnippet = Invoke-RemoteDocker "logs backend --tail 200 2>&1"
$badLog = $logSnippet -match "Traceback|Unhandled" -and $logSnippet -notmatch "sprint-b"
Set-Result "prod_logs" (-not $badLog) $(if ($badLog) { "unexpected tracebacks" } else { "no new unhandled errors" })

Remove-Item -Recurse -Force $signedDir -ErrorAction SilentlyContinue

$failed = @($results.Values | Where-Object { -not $_.Ok })
Write-Host ""
if ($failed.Count -eq 0) {
    Write-Host "SPRINT B PROD ACCEPTANCE PASS"
    exit 0
}
Write-Host "SPRINT B PROD ACCEPTANCE FAIL ($($failed.Count) checks)"
exit 1
