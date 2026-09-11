# Sprint E.5 production catalog + Sensibo closure (read-only)
param(
    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$KeyFile = $env:EMIC_DEPLOY_KEY,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE,
    [string]$SensiboApiKey = $env:SENSIBO_API_KEY,
    [string]$SiteSlug = "",
    [switch]$SkipDeploy
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
    throw "Deploy credentials required (EMIC_DEPLOY_PASSWORD or EMIC_DEPLOY_KEY)"
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

Write-Host "== Sprint E.5 prod closure =="
Write-Host "Target: $BaseUrl"
Write-Host ""

if (-not $SkipDeploy) {
    $pwFile = if ($PasswordFile) { $PasswordFile } elseif ($Password) {
        $tmp = Join-Path $env:TEMP "emic-deploy-pw.txt"
        Set-Content -Path $tmp -Value $Password -NoNewline
        $tmp
    } else { $null }
    $deployArgs = @("-Server", $Server, "-User", $User)
    if ($KeyFile) { $deployArgs += @("-KeyFile", $KeyFile) }
    if ($pwFile) {
        $deployArgs += @("-PasswordFile", $pwFile)
        if ($SudoPasswordFile) { $deployArgs += @("-SudoPasswordFile", $SudoPasswordFile) }
        elseif ($pwFile) { $deployArgs += @("-SudoPasswordFile", $pwFile) }
    }
    & "$repoRoot\scripts\deploy-linux.ps1" @deployArgs
    if ($pwFile -and -not $PasswordFile) { Remove-Item $pwFile -Force -ErrorAction SilentlyContinue }
}

$migrationOut = Invoke-RemoteDocker "exec -T backend alembic current"
Set-Result "migration_head" ($migrationOut -match "072_sensibo") $migrationOut

$token = (Invoke-Plink "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
Set-Result "admin_token" ([bool]$token) $(if ($token) { "present" } else { "missing" })
if (-not $token) { throw "EMIC_ADMIN_TOKEN missing on prod" }
$script:headers = @{ Authorization = "Bearer $token" }

if (-not $SensiboApiKey) {
    $envLine = (Invoke-Plink "grep -E '^SENSIBO_API_KEY=' ~/energy-monitoring/.env 2>/dev/null | head -1 | cut -d= -f2-").Trim()
    if ($envLine) { $SensiboApiKey = $envLine }
}

$sites = Invoke-EmicJson GET "/api/sites"
if (-not $SiteSlug) {
    $preferred = @($sites | Where-Object { $_.slug -eq "akarp" })
    if ($preferred.Count -ge 1) {
        $SiteSlug = "akarp"
    } else {
        $SiteSlug = ($sites | Select-Object -First 1).slug
    }
}
$siteIdLine = Invoke-Plink "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose exec -T postgres psql -U energy -d energy -tAc ""SELECT id FROM sites WHERE slug='${SiteSlug}' LIMIT 1;"""
$SiteId = 0
if ($siteIdLine -match '^\s*(\d+)\s*$') {
    $SiteId = [int]$Matches[1]
}
Set-Result "site_loaded" ([bool]$SiteSlug -and $SiteId -ge 1) "slug=$SiteSlug id=$SiteId"

$pkgSrc = Join-Path $repoRoot "packages\energy-core\tests\fixtures\modules\integration.sensibo-1.0.0.emicpkg"
$remotePkg = "/tmp/integration.sensibo-1.0.0.emicpkg"
& $pscp @authArgs $pkgSrc "${User}@${Server}:$remotePkg" | Out-Null
if ($Password) {
    Invoke-Plink "echo '$Password' | sudo -S mkdir -p ~/energy-monitoring/sprint-b-fixtures && echo '$Password' | sudo -S cp $remotePkg ~/energy-monitoring/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg && echo '$Password' | sudo -S chmod a+r ~/energy-monitoring/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg" | Out-Null
} else {
    Invoke-Plink "mkdir -p ~/energy-monitoring/sprint-b-fixtures && cp $remotePkg ~/energy-monitoring/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg" | Out-Null
}
& $pscp @authArgs (Join-Path $repoRoot "scripts\sprint-e-prod-setup-remote.py") "${User}@${Server}:energy-monitoring/scripts/sprint-e-prod-setup-remote.py" | Out-Null
Invoke-RemoteDocker "restart caddy" | Out-Null
Start-Sleep -Seconds 5

$fixtureBase = "http://caddy:8080"
$setupOut = Invoke-RemoteDocker "exec -T backend python /app/scripts/sprint-e-prod-setup-remote.py --fixture-base-url $fixtureBase --package-path /app/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg"
Set-Result "catalog_seed" ($setupOut -match "integration.sensibo") $setupOut

try {
    $detail = Invoke-EmicJson GET "/api/modules/store/integration.sensibo"
    Set-Result "store_detail" ($detail.summary.module_id -eq "integration.sensibo") $detail.summary.display_name
} catch {
    Set-Result "store_detail" $false $_.Exception.Message
}

try {
    $search = Invoke-EmicJson GET "/api/modules/store?search=sensibo"
    $found = @($search.modules | Where-Object { $_.module_id -eq "integration.sensibo" })
    Set-Result "store_search" ($found.Count -ge 1) "total=$($search.total)"
} catch {
    Set-Result "store_search" $false $_.Exception.Message
}

try {
    $preflight = Invoke-EmicJson POST "/api/modules/store/integration.sensibo/1.0.0/preflight" @{ site_slug = $SiteSlug }
    Set-Result "preflight" ($preflight.policy.decision -eq "ALLOW") $preflight.policy.decision
} catch {
    Set-Result "preflight" $false $_.Exception.Message
}

$pkgPath = Join-Path $repoRoot "packages\energy-core\tests\fixtures\modules\integration.sensibo-1.0.0.emicpkg"
try {
    $existing = Invoke-EmicJson GET "/api/modules/packages/integration.sensibo"
    Set-Result "install_stage" ($existing.package_state -in @("installed", "INSTALLED")) $existing.package_state
} catch {
    try {
        $form = @{ upload = Get-Item $pkgPath }
        $install = Invoke-RestMethod -Uri "$BaseUrl/api/modules/packages/install" -Method POST -Headers $script:headers -Form $form -TimeoutSec 180
        Set-Result "install_stage" ($install.success -eq $true) $install.package_state
    } catch {
        try {
            $install = Invoke-EmicJson POST "/api/modules/store/integration.sensibo/1.0.0/install" @{ site_slug = $SiteSlug; config = @{} }
            Set-Result "install_stage" ($install.package_state -in @("INSTALLED", "STAGED", "installed")) $install.package_state
        } catch {
            Set-Result "install_stage" $false $_.Exception.Message
        }
    }
}
Invoke-RemoteDocker "restart backend collector" | Out-Null
Start-Sleep -Seconds 20

if ($SensiboApiKey) {
    try {
        $cfg = Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.sensibo/external-config" @{
            api_key = $SensiboApiKey
            poll_interval_seconds = 300
            selected_device_ids = @()
        }
        Set-Result "credential_configured" ($cfg.credential_configured -eq $true) "configured=$($cfg.credential_configured)"
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
        Set-Result "discovery" ($disc.devices.Count -ge 0) "devices=$($disc.devices.Count)"
        if ($disc.devices.Count -ge 1 -and -not $cfg.selected_device_ids.Count) {
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
} else {
    Set-Result "credential_configured" $false "SENSIBO_API_KEY not set"
    Set-Result "connectivity" $false "skipped - no API key"
    Set-Result "discovery" $false "skipped - no API key"
}

try {
    $auths = Invoke-EmicJson GET "/api/modules/runtime/authorizations"
    $existing = @($auths | Where-Object { $_.module_id -eq "integration.sensibo" -and $_.site_id -eq $SiteId })
    if ($existing.Count -ge 1 -and $SiteId -ge 1) {
        Set-Result "runtime_authorization" $true "site_id=$SiteId existing=$($existing.Count)"
    } elseif ($SiteId -ge 1) {
        $pkg = Invoke-EmicJson GET "/api/modules/packages/integration.sensibo"
        $grantBody = @{
            module_id = "integration.sensibo"
            version = $pkg.installed_version
            artifact_sha256 = $pkg.checksum_sha256
            publisher_id = $pkg.publisher
            site_id = $SiteId
            reason = "Sprint E.5 prod closure"
        }
        $auth = Invoke-EmicJson POST "/api/modules/runtime/authorizations" $grantBody
        Set-Result "runtime_authorization" ($auth.module_id -eq "integration.sensibo") "site_id=$($auth.site_id)"
    } else {
        Set-Result "runtime_authorization" $false "site_id unresolved"
    }
} catch {
    Set-Result "runtime_authorization" $false $_.Exception.Message
}

try {
    $flags = Invoke-EmicJson GET "/api/system/modules"
    Set-Result "global_runtime_false" (-not [bool]$flags.third_party_runtime_enabled) "value=$($flags.third_party_runtime_enabled)"
} catch {
    Set-Result "global_runtime_false" $false $_.Exception.Message
}

try {
    Invoke-EmicJson PUT "/api/sites/$SiteSlug/modules/integration.sensibo" @{ enabled = $true } | Out-Null
    Set-Result "module_enabled" $true "enabled"
    Start-Sleep -Seconds 20
} catch {
    Set-Result "module_enabled" $false $_.Exception.Message
}

try {
    $climate = Invoke-RestMethod -Uri "$BaseUrl/api/sites/$SiteSlug/climate/devices" -TimeoutSec 30
    $count = @($climate.devices).Count
    Set-Result "climate_api" ($count -ge 0) "devices=$count"
    if ($count -ge 1 -and $SensiboApiKey) {
        $d = $climate.devices[0]
        Set-Result "real_temperature" ($null -ne $d.temperature_c) "temp=$($d.temperature_c)"
    }
} catch {
    Set-Result "climate_api" $false $_.Exception.Message
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

Write-Host ""
Write-Host "Running Linux Sensibo E2E on prod host..."
& "$repoRoot\scripts\run-linux-isolation-remote.ps1" -Server $Server -User $User -Password $Password -KeyFile $KeyFile -PasswordFile $PasswordFile -SudoPasswordFile $SudoPasswordFile
Set-Result "linux_sensibo_e2e" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

$failed = @($results.Values | Where-Object { -not $_.Ok })
Write-Host ""
Write-Host "Sprint E.5 closure: $($results.Count - $failed.Count)/$($results.Count) passed"
if ($failed.Count -gt 0) {
    Write-Host "FAILED checks:"
    $results.GetEnumerator() | Where-Object { -not $_.Value.Ok } | ForEach-Object { Write-Host "  $($_.Key): $($_.Value.Detail)" }
    exit 1
}
exit 0
