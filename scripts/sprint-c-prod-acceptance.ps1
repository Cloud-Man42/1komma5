# Sprint C.5 prod acceptance (Step 5C.5 runtime isolation — dormant deploy)



param(

    [string]$BaseUrl = $(if ($env:EMIC_BASE_URL) { $env:EMIC_BASE_URL } else { "https://192.168.50.54" }),

    [string]$Server = $env:EMIC_DEPLOY_SERVER,

    [string]$User = $env:EMIC_DEPLOY_USER,

    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,

    [string]$KeyFile = $env:EMIC_DEPLOY_KEY,

    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,

    [string]$SudoPasswordFile = $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE,

    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN

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

    if (-not (Test-Path $KeyFile)) { throw "Key file not found: $KeyFile" }

    $authArgs += @("-i", $KeyFile)

} elseif ($Password) {

    $authArgs += @("-pw", $Password)

} else {

    throw "PROD DEPLOY BLOCKED - CREDENTIALS REQUIRED"

}



$pscp = "C:\Program Files\PuTTY\pscp.exe"



function Invoke-Plink([string]$Command) {

    $prev = $ErrorActionPreference

    $ErrorActionPreference = "Continue"

    $out = (& $plink @authArgs "${User}@${Server}" $Command 2>&1 | Out-String).Trim()

    $ErrorActionPreference = $prev

    return $out

}



function Invoke-RemoteDocker([string]$DockerSubCommand) {

    if ($Password) {

        $cmd = "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose $DockerSubCommand 2>/dev/null"

        $sudoOut = Invoke-Plink $cmd

        if ($sudoOut) { return $sudoOut }

    }

    $plain = Invoke-Plink "cd ~/energy-monitoring && docker compose $DockerSubCommand"

    if ($plain -and $plain -notmatch "permission denied|sudo: a password is required|Cannot connect to the Docker daemon") {

        return $plain

    }

    if ($SudoPasswordFile -and (Test-Path $SudoPasswordFile)) {

        & $pscp @authArgs $SudoPasswordFile "${User}@${Server}:.emic-deploy-sudo" | Out-Null

        & $plink @authArgs "${User}@${Server}" "chmod 600 ~/.emic-deploy-sudo" | Out-Null

        $cmd = 'cd ~/energy-monitoring && sudo -S docker compose ' + $DockerSubCommand + ' < ~/.emic-deploy-sudo 2>/dev/null; rm -f ~/.emic-deploy-sudo'

        return Invoke-Plink $cmd

    }

    if ($Password) {

        $cmd = "cd ~/energy-monitoring && echo '$Password' | sudo -S docker compose $DockerSubCommand 2>&1"

        return Invoke-Plink $cmd

    }

    return $plain

}



$results = @{}

function Set-Result($Name, [bool]$Ok, [string]$Detail = "") {

    $script:results[$Name] = @{ Ok = $Ok; Detail = $Detail }

    $mark = if ($Ok) { "PASS" } else { "FAIL" }

    Write-Host "[$mark] $Name $(if ($Detail) { ": $Detail" })"

}



Write-Host "== Sprint C.5 prod acceptance (dormant runtime) =="

Write-Host "Target: $BaseUrl"

Write-Host ""



$migrationOut = Invoke-RemoteDocker "exec -T backend alembic current"

Set-Result "migration_069_prod" ($migrationOut -match "069_isolated_module_runtime") $migrationOut



$bwrapOut = Invoke-RemoteDocker "exec -T collector which bwrap"

Set-Result "collector_bwrap_present" ($bwrapOut -match "bwrap") $bwrapOut



$bootstrapOut = Invoke-RemoteDocker "exec -T collector ls /app/scripts/isolated_runtime_bootstrap.py"

Set-Result "collector_bootstrap_script" ($bootstrapOut -match "isolated_runtime_bootstrap") $bootstrapOut



$runtimeEnabledOut = Invoke-RemoteDocker "exec -T backend printenv THIRD_PARTY_RUNTIME_ENABLED"

Set-Result "third_party_runtime_disabled" (($runtimeEnabledOut -match "false") -or ($runtimeEnabledOut -eq "")) $runtimeEnabledOut



$controlGateOut = Invoke-RemoteDocker "exec -T backend printenv CONTROL_ISOLATION_GATE_OPEN"

Set-Result "control_gate_closed" (($controlGateOut -match "false") -or ($controlGateOut -eq "")) $controlGateOut



if (-not $AdminToken) {

    Set-Result "runtime_api_auth" $false "EMIC_ADMIN_TOKEN not set (required for runtime diagnostics auth)"

} else {

    try {

        $headers = @{ Authorization = "Bearer $AdminToken" }

        $body = Invoke-RestMethod -Uri "$BaseUrl/api/modules/runtime" -Headers $headers -TimeoutSec 15

        Set-Result "runtime_api_reachable" ($null -ne $body.runtimes) "list ok"

        Set-Result "runtime_api_blocked_flag" ($body.runtime_blocked -eq $true) "runtime_blocked=$($body.runtime_blocked)"

        try {

            Invoke-RestMethod -Uri "$BaseUrl/api/modules/runtime" -TimeoutSec 10 | Out-Null

            Set-Result "runtime_api_anonymous_denied" $false "anonymous request succeeded"

        } catch {

            Set-Result "runtime_api_anonymous_denied" $true "anonymous denied"

        }

    } catch {

        Set-Result "runtime_api_reachable" $false $_.Exception.Message

        Set-Result "runtime_api_blocked_flag" $false "unreachable"

        Set-Result "runtime_api_anonymous_denied" $false "unreachable"

    }

}



$failures = @($results.GetEnumerator() | Where-Object { -not $_.Value.Ok })

if ($failures.Count -gt 0) {

    Write-Host ""

    Write-Host "Sprint C.5 acceptance FAILED ($($failures.Count) checks)"

    exit 1

}

Write-Host ""

Write-Host "Sprint C.5 acceptance PASSED (dormant runtime deploy healthy)"

exit 0


