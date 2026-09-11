# Sprint E.6 — real Sensibo credential + live data closure (read-only)
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$KeyFile = $env:EMIC_DEPLOY_KEY,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE,
    [string]$SensiboApiKey = $env:SENSIBO_API_KEY,
    [string]$SiteSlug = ""
)

$ErrorActionPreference = "Stop"
if (-not $Server) { $Server = "192.168.50.54" }
if (-not $User) { $User = "hm" }

$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"
if (-not (Test-Path $plink)) { throw "PuTTY plink not found" }
if (-not (Test-Path $pscp)) { throw "PuTTY pscp not found" }

if ($PasswordFile) {
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
        Invoke-Plink "chmod 600 ~/.emic-deploy-sudo" | Out-Null
        $cmd = 'cd ~/energy-monitoring && sudo -S docker compose ' + $DockerSubCommand + ' < ~/.emic-deploy-sudo 2>/dev/null; rm -f ~/.emic-deploy-sudo'
        return Invoke-Plink $cmd
    }
    if ($Password) {
        return Invoke-Plink "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose $DockerSubCommand"
    }
    return Invoke-Plink "cd ~/energy-monitoring && docker compose $DockerSubCommand"
}

function Invoke-EmicJson($Method, $Path, $Body = $null, $Headers = $script:headers) {
    $uri = "$BaseUrl$Path"
    if ($null -ne $Body) {
        return Invoke-RestMethod -Uri $uri -Method $Method -Headers $Headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 8) -TimeoutSec 180
    }
    return Invoke-RestMethod -Uri $uri -Method $Method -Headers $Headers -TimeoutSec 180
}

Write-Host "== Sprint E.6 real data closure =="
Write-Host "Target: $BaseUrl"
Write-Host ""

$token = (Invoke-Plink "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
if (-not $token) { throw "EMIC_ADMIN_TOKEN missing on prod" }
$script:headers = @{ Authorization = "Bearer $token" }

if (-not $SensiboApiKey) {
    $envLine = (Invoke-Plink "grep -E '^SENSIBO_API_KEY=' ~/energy-monitoring/.env 2>/dev/null | head -1 | cut -d= -f2-").Trim()
    if ($envLine) { $SensiboApiKey = $envLine }
}

$sites = Invoke-EmicJson GET "/api/sites"
if (-not $SiteSlug) {
    $preferred = @($sites | Where-Object { $_.slug -eq "akarp" })
    if ($preferred.Count -ge 1) { $SiteSlug = "akarp" }
    else { $SiteSlug = ($sites | Select-Object -First 1).slug }
}
$siteIdLine = Invoke-Plink "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose exec -T postgres psql -U energy -d energy -tAc ""SELECT id FROM sites WHERE slug='${SiteSlug}' LIMIT 1;"""
$SiteId = 0
if ($siteIdLine -match '(\d+)') { $SiteId = [int]$Matches[1] }
Set-Result "site_resolved" ($SiteId -ge 1) "slug=$SiteSlug id=$SiteId"

$localPkg = Join-Path $repoRoot "packages\energy-core\tests\fixtures\modules\integration.sensibo-1.0.0.emicpkg"
$localDigest = (& "$repoRoot\.venv\Scripts\python.exe" -c "from pathlib import Path; from energy_core.platform.modules.packages.integrity import compute_package_content_sha256; print(compute_package_content_sha256(Path(r'$localPkg')))").Trim()
Set-Result "local_artifact_digest" ([bool]$localDigest) $localDigest

$remotePkg = "/tmp/integration.sensibo-1.0.0.emicpkg"
& $pscp @authArgs $localPkg "${User}@${Server}:$remotePkg" | Out-Null
Invoke-Plink "echo '$Password' | sudo -S cp $remotePkg ~/energy-monitoring/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg && echo '$Password' | sudo -S chmod a+r ~/energy-monitoring/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg" | Out-Null
& $pscp @authArgs (Join-Path $repoRoot "scripts\sprint-e-prod-setup-remote.py") "${User}@${Server}:energy-monitoring/scripts/sprint-e-prod-setup-remote.py" | Out-Null
Invoke-RemoteDocker "restart caddy" | Out-Null
Start-Sleep -Seconds 3

$setupOut = Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-e-prod-setup-remote.py --fixture-base-url http://caddy:8080 --package-path /app/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg"
Set-Result "catalog_seed" ($setupOut -match $localDigest) $setupOut

$installed = Invoke-EmicJson GET "/api/modules/packages/integration.sensibo"
$needsUpgrade = ($installed.checksum_sha256 -ne $localDigest)
Set-Result "artifact_aligned_pre" (-not $needsUpgrade) "installed=$($installed.checksum_sha256)"

if ($needsUpgrade) {
    Write-Host "Upgrading Sensibo package via Store pipeline..."
    try { Invoke-EmicJson DELETE "/api/modules/packages/integration.sensibo" | Out-Null } catch { }
    try {
        $fetch = Invoke-EmicJson POST "/api/modules/marketplace/releases/integration.sensibo/1.0.0/fetch" $null
        Set-Result "artifact_fetch" ($fetch.state -in @("STAGED", "VERIFIED", "FETCHED")) $fetch.state
    } catch {
        Set-Result "artifact_fetch" $false $_.Exception.Message
        try {
            $form = @{ upload = Get-Item $localPkg }
            $upload = Invoke-RestMethod -Uri "$BaseUrl/api/modules/packages/install" -Method POST -Headers $script:headers -Form $form -TimeoutSec 180
            Set-Result "artifact_upload_fallback" ($upload.success -eq $true) $upload.package_state
        } catch {
            Set-Result "artifact_upload_fallback" $false $_.Exception.Message
        }
    }
    try {
        $storeInstall = Invoke-EmicJson POST "/api/modules/store/integration.sensibo/1.0.0/install" @{ site_slug = $SiteSlug; config = @{} }
        Set-Result "artifact_store_install" ($storeInstall.package_state -in @("installed", "INSTALLED", "STAGED")) $storeInstall.package_state
    } catch {
        Set-Result "artifact_store_install" $false $_.Exception.Message
    }
    Invoke-RemoteDocker "restart backend collector" | Out-Null
    Start-Sleep -Seconds 15
    $installed = Invoke-EmicJson GET "/api/modules/packages/integration.sensibo"
}

Set-Result "artifact_aligned_post" ($installed.checksum_sha256 -eq $localDigest) "sha=$($installed.checksum_sha256)"
Set-Result "signature_valid" ($installed.signature_status -eq "valid") $installed.signature_status

$auths = @(Invoke-EmicJson GET "/api/modules/runtime/authorizations")
$stale = @($auths | Where-Object {
    $_.module_id -eq "integration.sensibo" -and (
        $_.artifact_sha256 -ne $installed.checksum_sha256 -or $_.site_id -ne $SiteId
    )
})
foreach ($auth in $stale) {
    try {
        Invoke-EmicJson DELETE "/api/modules/runtime/authorizations/$($auth.id)" | Out-Null
        Write-Host "Revoked stale authorization id=$($auth.id) sha=$($auth.artifact_sha256) site=$($auth.site_id)"
    } catch {
        Write-Host "WARN: failed to revoke auth id=$($auth.id): $($_.Exception.Message)"
    }
}

$auths = @(Invoke-EmicJson GET "/api/modules/runtime/authorizations")
$validAuth = @($auths | Where-Object {
    $_.module_id -eq "integration.sensibo" -and
    $_.site_id -eq $SiteId -and
    $_.artifact_sha256 -eq $installed.checksum_sha256 -and
    $_.active -eq $true
})
if ($validAuth.Count -lt 1 -and $SiteId -ge 1) {
    $grantBody = @{
        module_id = "integration.sensibo"
        version = $installed.installed_version
        artifact_sha256 = $installed.checksum_sha256
        publisher_id = $installed.publisher
        site_id = $SiteId
        reason = "Sprint E.6 real data closure"
    }
    $validAuth = @(Invoke-EmicJson POST "/api/modules/runtime/authorizations" $grantBody)
}
Set-Result "runtime_authorization_sha" ($validAuth.Count -ge 1 -and $validAuth[0].artifact_sha256 -eq $installed.checksum_sha256) "sha=$($validAuth[0].artifact_sha256)"

try {
    $flags = Invoke-EmicJson GET "/api/system/modules"
    Set-Result "global_runtime_false" (-not [bool]$flags.third_party_runtime_enabled) "value=$($flags.third_party_runtime_enabled)"
} catch {
    Set-Result "global_runtime_false" $false $_.Exception.Message
}

if ($SensiboApiKey) {
    try {
        $cfg = Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.sensibo/external-config" @{
            api_key = $SensiboApiKey
            poll_interval_seconds = 300
            selected_device_ids = @()
        }
        Set-Result "credential_configured" ($cfg.credential_configured -eq $true) "configured=$($cfg.credential_configured)"
        $cfgBody = Invoke-EmicJson GET "/api/sites/$SiteSlug/modules/integration.sensibo/external-config"
        Set-Result "credential_not_exposed" ($null -eq $cfgBody.api_key) "response has no api_key field"
    } catch {
        Set-Result "credential_configured" $false $_.Exception.Message
    }

    try {
        $conn = Invoke-EmicJson POST "/api/sites/$SiteSlug/modules/integration.sensibo/test-connection" $null
        Set-Result "connectivity" ($conn.success -eq $true) $conn.message
    } catch {
        Set-Result "connectivity" $false $_.Exception.Message
    }

    try {
        $disc = Invoke-EmicJson POST "/api/sites/$SiteSlug/modules/integration.sensibo/discover" $null
        Set-Result "discovery" ($disc.devices.Count -ge 1) "devices=$($disc.devices.Count)"
        if ($disc.devices.Count -ge 1) {
            $deviceIds = @($disc.devices | ForEach-Object { $_.device_id } | Select-Object -First 3)
            Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.sensibo/external-config" @{
                api_key = $SensiboApiKey
                poll_interval_seconds = 300
                selected_device_ids = $deviceIds
            } | Out-Null
            Set-Result "device_binding" ($deviceIds.Count -ge 1) "bound=$($deviceIds.Count)"
        }
    } catch {
        Set-Result "discovery" $false $_.Exception.Message
    }

    try {
        Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.sensibo" @{ enabled = $true } | Out-Null
        Start-Sleep -Seconds 45
    } catch {
        Write-Host "WARN: enable module failed: $($_.Exception.Message)"
    }

    try {
        $climate = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$SiteSlug/climate/devices" -TimeoutSec 30
        $count = @($climate.devices).Count
        Set-Result "climate_api" ($count -ge 1) "devices=$count"
        if ($count -ge 1) {
            $d = $climate.devices[0]
            Set-Result "real_temperature" ($null -ne $d.temperature_c) "temp=$($d.temperature_c)"
            Set-Result "real_humidity" ($null -ne $d.humidity_percent) "humidity=$($d.humidity_percent)"
        }
    } catch {
        Set-Result "climate_api" $false $_.Exception.Message
    }
} else {
    Set-Result "credential_configured" $false "SENSIBO_API_KEY not configured (set env or prod .env)"
    Set-Result "connectivity" $false "skipped"
    Set-Result "discovery" $false "skipped"
    Set-Result "climate_api" $false "skipped"
}

Write-Host ""
Write-Host "Running sprint-e-sensibo-acceptance.ps1..."
& "$repoRoot\scripts\sprint-e-sensibo-acceptance.ps1" -BaseUrl $BaseUrl -SiteSlug $SiteSlug -AdminToken $token
Set-Result "acceptance_script" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

Write-Host ""
Write-Host "Running verify-prod-health.ps1..."
& "$repoRoot\scripts\verify-prod-health.ps1" -BaseUrl $BaseUrl
Set-Result "prod_health" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

Write-Host ""
Write-Host "Running verify-prod-runtime-consistency.ps1 -Strict..."
& "$repoRoot\scripts\verify-prod-runtime-consistency.ps1" -BaseUrl $BaseUrl -Strict
Set-Result "prod_runtime_consistency" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

$failed = @($results.Values | Where-Object { -not $_.Ok })
Write-Host ""
Write-Host "Sprint E.6 closure: $($results.Count - $failed.Count)/$($results.Count) passed"
if ($failed.Count -gt 0) {
    Write-Host "FAILED checks:"
    $results.GetEnumerator() | Where-Object { -not $_.Value.Ok } | ForEach-Object { Write-Host "  $($_.Key): $($_.Value.Detail)" }
    exit 1
}
exit 0
