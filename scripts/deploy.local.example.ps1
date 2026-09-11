# Example local deploy script — copy to deploy.local.ps1 and adjust paths.
# deploy.local.ps1 is gitignored.

$ErrorActionPreference = "Stop"

$env:EMIC_DEPLOY_SERVER = "192.168.50.54"
$env:EMIC_DEPLOY_USER = "hm"

# Preferred: SSH key
# $env:EMIC_DEPLOY_KEY = "$env:USERPROFILE\.ssh\emic-deploy.ppk"

# Or password files (never commit these):
# Create:  echo your-ssh-password > %USERPROFILE%\.emic-deploy-password
# Create:  echo your-sudo-password > %USERPROFILE%\.emic-deploy-sudo

$passwordFile = Join-Path $env:USERPROFILE ".emic-deploy-password"
$sudoFile = Join-Path $env:USERPROFILE ".emic-deploy-sudo"

if (Test-Path $passwordFile) {
    $env:EMIC_DEPLOY_PASSWORD_FILE = $passwordFile
}

if (Test-Path $sudoFile) {
    $env:EMIC_DEPLOY_SUDO_PASSWORD_FILE = $sudoFile
}

& "$PSScriptRoot\deploy-linux.ps1"
