param(
    [string]$BaseUrl = "http://192.168.50.54",
    [string]$Site = "akarp",
    [string]$Server = $env:EMIC_DEPLOY_SERVER,
    [string]$User = $env:EMIC_DEPLOY_USER,
    [string]$Password = $env:EMIC_DEPLOY_PASSWORD,
    [string]$PasswordFile = $env:EMIC_DEPLOY_PASSWORD_FILE,
    [string]$AdminToken = $env:EMIC_ADMIN_TOKEN
)

$ErrorActionPreference = "Stop"

if ($PasswordFile -and (Test-Path $PasswordFile)) {
    $Password = (Get-Content -Path $PasswordFile -Raw).Trim()
}
if (-not $Server) { $Server = ([uri]$BaseUrl).Host }
if (-not $User) { $User = "hm" }

if (-not $AdminToken) {
    $plink = "C:\Program Files\PuTTY\plink.exe"
    if (Test-Path $plink) {
        $authArgs = @("-batch")
        if ($Password) { $authArgs += @("-pw", $Password) }
        $AdminToken = (& $plink @authArgs "${User}@${Server}" "grep -E '^EMIC_ADMIN_TOKEN=' ~/energy-monitoring/.env | head -1 | cut -d= -f2-").Trim()
    }
}

if (-not $AdminToken) {
    throw "Set EMIC_ADMIN_TOKEN or configure SSH access to read it from prod .env"
}

$headers = @{
    Authorization = "Bearer $AdminToken"
    "Content-Type" = "application/json"
}

$body = @{
    owner_label = "EMIC benchmark"
    device_name = "Pi benchmark $(Get-Date -Format 'yyyyMMdd-HHmm')"
    device_type = "raspberry_pi"
    default_site_slug = $Site
} | ConvertTo-Json

Write-Host "Creating display.read device for Pi benchmark..."
$res = Invoke-RestMethod -Uri "$BaseUrl/api/apple-devices" -Method Post -Headers $headers -Body $body
Write-Host "  device_id=$($res.id) scopes=$($res.scopes)"
$env:EMIC_DISPLAY_TOKEN = $res.token
Write-Host "EMIC_DISPLAY_TOKEN set for this session."

& "$PSScriptRoot\phase20-pi-baseline.ps1" -BaseUrl $BaseUrl -Site $Site -DisplayToken $res.token
