function Get-EmicDeployAuthArgs {
    param(
        [string]$KeyFile = $env:EMIC_DEPLOY_KEY,
        [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
        [string]$Password = $env:EMIC_DEPLOY_PASSWORD
    )

    if ($PasswordFile) {
        if (-not (Test-Path $PasswordFile)) {
            throw "Password file not found: $PasswordFile"
        }
        $Password = (Get-Content -Path $PasswordFile -Raw).Trim()
    }

    if ($KeyFile) {
        if (-not (Test-Path $KeyFile)) {
            throw "Key file not found: $KeyFile"
        }
        return @("-batch", "-i", $KeyFile)
    }

    if ($Password) {
        return @("-batch", "-pw", $Password)
    }

    throw "Set EMIC_DEPLOY_KEY, EMIC_DEPLOY_PASSWORD_FILE, or EMIC_DEPLOY_PASSWORD"
}

function Invoke-EmicRestMethod {
    param(
        [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
        [object[]]$RestArgs
    )

    if ($PSVersionTable.PSVersion.Major -ge 7) {
        return Invoke-RestMethod @RestArgs -SkipCertificateCheck
    }
    return Invoke-RestMethod @RestArgs
}

function Get-EmicAdminTokenFromRemote {
    param(
        [string]$PlinkPath = "C:\Program Files\PuTTY\plink.exe",
        [string]$User = "hm",
        [string]$Server = "192.168.50.54",
        [string]$RemoteEnvPath = "~/energy-monitoring/.env"
    )

    if (-not (Test-Path $PlinkPath)) {
        throw "PuTTY plink not found at $PlinkPath"
    }

    $authArgs = Get-EmicDeployAuthArgs
    $token = (& $PlinkPath @authArgs "${User}@${Server}" "grep -E '^EMIC_ADMIN_TOKEN=' $RemoteEnvPath | head -1 | cut -d= -f2-").Trim()
    if (-not $token) {
        throw "EMIC_ADMIN_TOKEN not found in remote $RemoteEnvPath"
    }
    return $token
}
