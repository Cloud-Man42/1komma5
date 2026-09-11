# Sprint A production governance acceptance (evaluate-only dry-runs)
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE
)

$ErrorActionPreference = "Stop"
if (-not $Server) { $Server = "192.168.50.54" }
if (-not $User) { $User = "hm" }
$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"

$results = @{}
function Set-Result($Name, [bool]$Ok, [string]$Detail = "") {
    $script:results[$Name] = @{ Ok = $Ok; Detail = $Detail }
    $mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "[$mark] $Name $(if ($Detail) { ": $Detail" })"
}

Write-Host "Sprint A prod governance acceptance: $BaseUrl"
Write-Host ""

# Anonymous governance denied
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers" -TimeoutSec 15 | Out-Null
    Set-Result "anonymous_governance_denied" $false "expected 401/403, got 200"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Set-Result "anonymous_governance_denied" ($code -in 401,403) "HTTP $code"
}

# Admin token
$token = (& $plink -batch -pw $Password "${User}@${Server}" "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
Set-Result "admin_token_configured" ([bool]$token) $(if ($token) { "token present" } else { "EMIC_ADMIN_TOKEN empty" })
if (-not $token) {
    Write-Host "BLOCKER: cannot continue prod dry-runs without admin token"
    exit 1
}
$headers = @{ Authorization = "Bearer $token" }

# Governance route registered
try {
    $pubs = Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers" -Headers $headers -TimeoutSec 15
    Set-Result "governance_route_registered" $true "publishers=$($pubs.Count)"
} catch {
    Set-Result "governance_route_registered" $false $_.Exception.Message
}

function Invoke-Eval($Body) {
    return Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/evaluate" -Method POST -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json) -TimeoutSec 15
}

# Ensure test publishers exist (idempotent setup)
function Ensure-Publisher($Id, $DisplayName, $Tier) {
    try {
        Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers" -Method POST -Headers $headers -ContentType "application/json" -Body (@{ publisher_id = $Id; display_name = $DisplayName; tier = $Tier } | ConvertTo-Json) -TimeoutSec 15 | Out-Null
    } catch {
        # may already exist
    }
}
function Ensure-Verified($Id) {
    try { Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers/$Id/verify" -Method POST -Headers $headers -TimeoutSec 15 | Out-Null } catch {}
}
function Ensure-Revoked($Id) {
    try { Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers/$Id/revoke" -Method POST -Headers $headers -TimeoutSec 15 | Out-Null } catch {}
}
function Ensure-Suspended($Id) {
    try { Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers/$Id/suspend" -Method POST -Headers $headers -TimeoutSec 15 | Out-Null } catch {}
}

Ensure-Publisher "emic" "EMIC Official" "OFFICIAL"
Ensure-Verified "emic"
Ensure-Publisher "sprint-a-community" "Community Test" "COMMUNITY"
# COMMUNITY tier must remain unverified (verify upgrades COMMUNITY -> VERIFIED)
Ensure-Publisher "sprint-a-revoked" "Revoked Test" "ORG_APPROVED"
Ensure-Verified "sprint-a-revoked"
Ensure-Revoked "sprint-a-revoked"
Ensure-Publisher "sprint-a-suspended" "Suspended Test" "ORG_APPROVED"
Ensure-Verified "sprint-a-suspended"
Ensure-Suspended "sprint-a-suspended"
Ensure-Publisher "sprint-a-owner-a" "Owner A" "VERIFIED"
Ensure-Verified "sprint-a-owner-a"
Ensure-Publisher "sprint-a-owner-b" "Owner B" "VERIFIED"
Ensure-Verified "sprint-a-owner-b"

function Invoke-RemoteDocker([string]$DockerSubCommand) {
    if ($SudoPasswordFile -and (Test-Path $SudoPasswordFile)) {
        & $pscp -batch -pw $Password $SudoPasswordFile "${User}@${Server}:.emic-deploy-sudo" | Out-Null
        & $plink -batch -pw $Password "${User}@${Server}" "chmod 600 ~/.emic-deploy-sudo" | Out-Null
        $cmd = "cd ~/energy-monitoring && sudo -S docker compose $DockerSubCommand < ~/.emic-deploy-sudo 2>/dev/null; rm -f ~/.emic-deploy-sudo"
    } else {
        $cmd = "cd ~/energy-monitoring && docker compose $DockerSubCommand"
    }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = (& $plink -batch -pw $Password "${User}@${Server}" $cmd 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $prev
    return $out
}

# Ownership setup via remote helper script (requires EMIC_DEPLOY_SUDO_PASSWORD_FILE)
if ($SudoPasswordFile -and (Test-Path $SudoPasswordFile)) {
    $setupScript = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\sprint-a-prod-setup-remote.sh"
    $setupUnix = Join-Path $env:TEMP "sprint-a-prod-setup-remote-unix.sh"
    $sudoUnix = Join-Path $env:TEMP "emic-deploy-sudo-unix"
    (Get-Content $setupScript -Raw).Replace("`r`n", "`n") | Set-Content -Path $setupUnix -NoNewline
    (Get-Content $SudoPasswordFile -Raw).Trim() | Set-Content -Path $sudoUnix -NoNewline
    & $pscp -batch -pw $Password $setupUnix "${User}@${Server}:sprint-a-prod-setup.sh" | Out-Null
    & $pscp -batch -pw $Password $sudoUnix "${User}@${Server}:.emic-deploy-sudo" | Out-Null
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $plink -batch -pw $Password "${User}@${Server}" "chmod 600 ~/.emic-deploy-sudo && bash ~/sprint-a-prod-setup.sh" 2>&1 | Out-Null
    $ErrorActionPreference = $prev
}
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers/sprint-a-community" -Method PATCH -Headers $headers -ContentType "application/json" -Body (@{ tier = "COMMUNITY" } | ConvertTo-Json) -TimeoutSec 15 | Out-Null
} catch {}

# OFFICIAL allow
$r = Invoke-Eval @{ module_id = "emic.core"; publisher_id = "emic"; action = "INSTALL" }
Set-Result "official_allow" ($r.decision -eq "ALLOW") "$($r.decision) $($r.reason_codes -join ',')"

# COMMUNITY deny
$r = Invoke-Eval @{ module_id = "demo.mod"; publisher_id = "sprint-a-community"; action = "INSTALL" }
Set-Result "community_deny" ($r.decision -eq "DENY") "$($r.decision) $($r.reason_codes -join ',')"

# REVOKED deny
$r = Invoke-Eval @{ module_id = "demo.mod"; publisher_id = "sprint-a-revoked"; action = "INSTALL" }
Set-Result "revoked_deny" ($r.decision -eq "DENY") "$($r.decision) $($r.reason_codes -join ',')"

# SUSPENDED deny
$r = Invoke-Eval @{ module_id = "demo.mod"; publisher_id = "sprint-a-suspended"; action = "INSTALL" }
Set-Result "suspended_deny" ($r.decision -eq "DENY") "$($r.decision) $($r.reason_codes -join ',')"

# Ownership mismatch
$r = Invoke-Eval @{ module_id = "sprint-a.ownership-test"; publisher_id = "sprint-a-owner-b"; action = "INSTALL" }
Set-Result "ownership_mismatch_deny" ($r.decision -eq "DENY" -and ($r.reason_codes -contains "OWNERSHIP_MISMATCH")) "$($r.decision) $($r.reason_codes -join ',')"

# Control RUN pre-5C.5 deny
$r = Invoke-Eval @{ module_id = "demo.control"; publisher_id = "sprint-a-owner-a"; action = "RUN"; permissions = @("device.control"); provided_capabilities = @("device.control") }
Set-Result "control_run_deny" ($r.decision -eq "DENY") "$($r.decision) $($r.reason_codes -join ',')"

# Active revocation + break-glass deny
Ensure-Publisher "sprint-a-revoke-bg" "Revoke BG Test" "ORG_APPROVED"
Ensure-Verified "sprint-a-revoke-bg"
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/modules/governance/publishers/sprint-a-revoke-bg/revoke" -Method POST -Headers $headers -ContentType "application/json" -Body (@{ severity = "LOW"; reason = "sprint-a dry-run" } | ConvertTo-Json) -TimeoutSec 15 | Out-Null
} catch {}
$r = Invoke-Eval @{ module_id = "demo.mod"; publisher_id = "sprint-a-revoke-bg"; action = "INSTALL"; break_glass_active = $true }
Set-Result "revocation_break_glass_deny" ($r.decision -eq "DENY") "$($r.decision) $($r.reason_codes -join ',')"

# Marketplace status route
try {
    $ms = Invoke-RestMethod -Uri "$BaseUrl/api/modules/marketplace/status" -Headers $headers -TimeoutSec 15
    Set-Result "marketplace_status_route" $true "enabled=$($ms.enabled)"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Set-Result "marketplace_status_route" ($code -ne 404) "HTTP $code"
}

# Migration 067 via remote alembic
$alembicOut = Invoke-RemoteDocker "exec -T backend alembic current"
Set-Result "migration_067" ($alembicOut -match "067_module_governance") $alembicOut

$tableOut = Invoke-RemoteDocker "exec -T postgres psql -U energy -d energy -c '\dt module_*'"
$required = @("module_publishers","module_publisher_verifications","module_ownership","module_ownership_transfers","module_installation_policy","module_policy_history")
$missing = @($required | Where-Object { $tableOut -notmatch [regex]::Escape($_) })
Set-Result "governance_tables" ($missing.Count -eq 0) $(if ($missing.Count) { "missing: $($missing -join ',')" } else { "all present" })

Write-Host ""
$failed = @($results.Keys | Where-Object { -not $results[$_].Ok })
if ($failed.Count -eq 0) {
    Write-Host "SPRINT A PROD GOVERNANCE ACCEPTANCE PASS"
    exit 0
}
Write-Host "FAILED: $($failed -join ', ')"
exit 1
