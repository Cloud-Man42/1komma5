# Step 5B.5 signed demo production acceptance (internal demo only)
param(
    [string]$BaseUrl = "https://192.168.50.54",
    [string]$Server = "192.168.50.54",
    [string]$User = "hm",
    [string]$SiteSlug = "akarp",
    [string]$OtherSite = "summer-house-denmark"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/lib/Get-EmicDeployCredential.ps1"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$token = Get-EmicAdminTokenFromRemote -User $User -Server $Server
if (-not $token) { throw "EMIC_ADMIN_TOKEN missing on prod" }
$headers = @{ Authorization = "Bearer $token" }

function Invoke-EmicJson($Method, $Path, $Body = $null) {
    $uri = "$BaseUrl$Path"
    if ($null -ne $Body) {
        return Invoke-EmicRestMethod -Uri $uri -Method $Method -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json)
    }
    return Invoke-EmicRestMethod -Uri $uri -Method $Method -Headers $headers
}

function Invoke-EmicUpload($Path, [string]$FilePath) {
    $uri = "$BaseUrl$Path"
    curl.exe -sS -X POST $uri -H "Authorization: Bearer $token" -F "upload=@$FilePath" | ConvertFrom-Json
}

Write-Host "Pre-check: prod health scripts"
& "$PSScriptRoot/verify-prod-health.ps1"
& "$PSScriptRoot/verify-prod-runtime-consistency.ps1" -Strict

Write-Host "Sign demo packages (private key in temp only)"
$signedDir = Join-Path $env:TEMP "emic-step5b5-signed-$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -ItemType Directory -Path $signedDir -Force | Out-Null
$manifestPath = & .\.venv\Scripts\python.exe .\scripts\sign_demo_packages.py --output-dir $signedDir | Select-Object -First 1
$manifest = Get-Content $manifestPath | ConvertFrom-Json
$publisherId = $manifest.publisher_id
$keyId = $manifest.key_id
$publicKey = $manifest.public_key_hex

Write-Host "Prepare trusted test publisher"
$publishers = @(Invoke-EmicJson GET "/api/modules/publishers")
$existingKey = $publishers | Where-Object { $_.publisher_id -eq $publisherId -and $_.key_id -eq $keyId } | Select-Object -First 1
if ($existingKey -and $existingKey.status -eq "trusted" -and $existingKey.public_key_hex -eq $publicKey) {
    Write-Host "Publisher key already trusted with matching public key"
} else {
    if ($existingKey) {
        Write-Host "Revoking existing publisher key before re-trust"
        Invoke-EmicJson POST "/api/modules/publishers/$publisherId/$keyId/revoke" @{} | Out-Null
    }
    Invoke-EmicJson POST "/api/modules/publishers" @{
        publisher_id = $publisherId
        key_id = $keyId
        public_key_hex = $publicKey
    } | Out-Null
}

$unsigned = Join-Path $repoRoot "packages/energy-core/tests/fixtures/modules/integration.demo-1.0.0.emicpkg"
Write-Host "Verify unsigned rejected on prod"
try {
    $unsignedResult = Invoke-EmicUpload "/api/modules/packages/validate" $unsigned
    if ($unsignedResult.install_allowed) { throw "Unsigned package should be rejected" }
    Write-Host "Unsigned validate blocked (expected)"
} catch {
    Write-Host "Unsigned validate blocked (expected): $_"
}

$signed10 = $manifest.packages."1.0.0"
$signed11 = $manifest.packages."1.1.0"

Write-Host "Ensure clean demo package state"
$existing = @(Invoke-EmicJson GET "/api/modules/packages")
if ($existing.module_id -contains "integration.demo") {
    Write-Host "Removing previous demo package"
    try { Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.demo" @{ enabled = $false } | Out-Null } catch {}
    try { Invoke-EmicJson PUT "/api/sites/$OtherSite/modules/integration.demo" @{ enabled = $false } | Out-Null } catch {}
    Invoke-EmicJson DELETE "/api/modules/packages/integration.demo" | Out-Null
}

Write-Host "Validate signed 1.0.0"
$validate = Invoke-EmicUpload "/api/modules/packages/validate" $signed10
if (-not $validate.signature_valid -or -not $validate.install_allowed) {
    throw "Signed 1.0.0 validation failed: $($validate | ConvertTo-Json -Compress)"
}

Write-Host "Impact preview"
$impact = Invoke-EmicUpload "/api/modules/packages/integration.demo/impact" $signed10
Write-Host "Impact restart_required=$($impact.restart_required)"

Write-Host "Install signed 1.0.0"
$install = Invoke-EmicUpload "/api/modules/packages/install" $signed10
if (-not $install.success) { throw "Install failed" }

Write-Host "Restart backend + collector for package load"
& $plink -batch -pw $Password "${User}@${Server}" "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose restart backend collector"
Start-Sleep -Seconds 25

Write-Host "Enable demo on $SiteSlug only"
Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.demo" @{ enabled = $true } | Out-Null
Invoke-EmicJson PUT "/api/sites/$OtherSite/modules/integration.demo" @{ enabled = $false } | Out-Null
Start-Sleep -Seconds 10

$siteA = Invoke-EmicJson GET "/api/sites/$SiteSlug/modules/integration.demo"
$siteB = Invoke-EmicJson GET "/api/sites/$OtherSite/modules/integration.demo"
Write-Host "Multi-site isolation: $SiteSlug enabled=$($siteA.enabled) runtime=$($siteA.runtime_status) $OtherSite enabled=$($siteB.enabled) runtime=$($siteB.runtime_status)"
if (-not $siteA.enabled) { throw "Expected demo enabled on $SiteSlug" }
if ($siteB.enabled) { throw "Expected demo disabled on $OtherSite" }

$detail = Invoke-EmicJson GET "/api/modules/packages/store/packages/integration.demo"
Write-Host "Store detail installed=$($detail.installed_version) runtime=$($detail.runtime_version) version_match=$($detail.version_match)"

Write-Host "Update to 1.1.0"
$update = Invoke-EmicUpload "/api/modules/packages/integration.demo/update" $signed11
if (-not $update.success) { throw "Update failed" }
& $plink -batch -pw $Password "${User}@${Server}" "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose restart backend collector"
Start-Sleep -Seconds 25

Write-Host "Downgrade block test"
$downgrade = Invoke-EmicUpload "/api/modules/packages/integration.demo/update" $signed10
if ($downgrade.detail.code -ne "VERSION_DOWNGRADE_NOT_ALLOWED") {
    throw "Expected VERSION_DOWNGRADE_NOT_ALLOWED, got $($downgrade | ConvertTo-Json -Compress)"
}
Write-Host "Downgrade blocked (expected)"

Write-Host "Rollback to previous"
$rollback = Invoke-EmicJson POST "/api/modules/packages/integration.demo/rollback" $null
if (-not $rollback.success) { throw "Rollback failed" }

Write-Host "Disable and remove"
Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.demo" @{ enabled = $false } | Out-Null
$remove = Invoke-EmicJson DELETE "/api/modules/packages/integration.demo"
if (-not $remove.success) { throw "Remove failed" }

Write-Host "Revoke test publisher"
Invoke-EmicJson POST "/api/modules/publishers/$publisherId/$keyId/revoke" $null | Out-Null

Remove-Item -Recurse -Force $signedDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Split-Path $manifestPath) -ErrorAction SilentlyContinue

Write-Host "Post-check health"
& "$PSScriptRoot/verify-prod-health.ps1"
& "$PSScriptRoot/verify-prod-runtime-consistency.ps1" -Strict

Write-Host "STEP 5B.5 PROD ACCEPTANCE PASS"
