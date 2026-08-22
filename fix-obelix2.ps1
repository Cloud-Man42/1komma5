param(
    [Parameter(Mandatory = $true)]
    [string]$Password,

    [string]$Server = 'vcenter6.galjonen.local',
    [string]$User = 'administrator@vsphere.local',
    [string]$VmName = 'Obelix2',
    [string]$EsxiHost = '192.168.0.20'
)

Set-PowerCLIConfiguration -Scope User -InvalidCertificateAction Ignore -Confirm:$false | Out-Null

$sec = ConvertTo-SecureString $Password -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential($User, $sec)

Write-Host "Connecting to vCenter $Server..."
$vi = Connect-VIServer -Server $Server -Credential $cred -Force

try {
    $vm = Get-VM -Name $VmName -ErrorAction Stop
    Write-Host "Found VM: $($vm.Name) | PowerState: $($vm.PowerState) | Path: $($vm.ExtensionData.Config.Files.VmPathName)"

    $hostObj = Get-VMHost -Name $EsxiHost -ErrorAction SilentlyContinue
    if (-not $hostObj) {
        $hostObj = $vm.VMHost
    }
    Write-Host "Host: $($hostObj.Name)"

    Write-Host "Searching datastores for $VmName.vmx..."
    $foundVmx = @()
    foreach ($ds in Get-Datastore -VMHost $hostObj) {
        Write-Host "  Checking datastore: $($ds.Name)"
        try {
            $dsObj = Get-View -Id $ds.ExtensionData.MoRef
            $browser = Get-View -Id $dsObj.Browser
            $search = $browser.SearchDatastoreSubFolders_Task($ds.ExtensionData.MoRef, "*$VmName*.vmx", $null)
            while ($search.Runtime.State -eq 'running' -or $search.Runtime.State -eq 'queued') {
                Start-Sleep -Milliseconds 500
                $search = Get-View -Id $search.MoRef
            }
            if ($search.Info.Result) {
                foreach ($item in $search.Info.Result) {
                    $path = $item.FolderPath + $item.File[0].Path
                    Write-Host "  FOUND: $path on $($ds.Name)"
                    $foundVmx += [PSCustomObject]@{ Datastore = $ds.Name; Path = $path }
                }
            }
        } catch {
            Write-Warning "  Could not search $($ds.Name): $($_.Exception.Message)"
        }
    }

    if ($foundVmx.Count -eq 0) {
        Write-Error "No $VmName.vmx found on any datastore. VM files may be deleted - restore from backup."
        exit 2
    }

    $target = $foundVmx[0]
    $registerPath = "[$($target.Datastore)] $($target.Path -replace '^\[.*?\]\s*','')"

    if ($vm.ExtensionData.Config.Files.VmPathName -ne $registerPath) {
        Write-Host "VM path mismatch. Removing stale inventory entry..."
        $vm | Remove-VM -Confirm:$false
        Write-Host "Registering VM from: $registerPath"
        New-VM -VMHost $hostObj -Name $VmName -VM $registerPath -ErrorAction Stop | Out-Null
        $vm = Get-VM -Name $VmName
    } else {
        Write-Host "VM path looks correct; trying unregister/reregister..."
        $vm | Remove-VM -Confirm:$false
        New-VM -VMHost $hostObj -Name $VmName -VM $registerPath -ErrorAction Stop | Out-Null
        $vm = Get-VM -Name $VmName
    }

    Write-Host "Starting $VmName..."
    Start-VM -VM $vm -Confirm:$false | Out-Null
    Start-Sleep -Seconds 5
    $vm = Get-VM -Name $VmName
    Write-Host "Done. PowerState: $($vm.PowerState)"
    if ($vm.PowerState -ne 'PoweredOn') {
        Write-Error "VM did not reach PoweredOn state."
        exit 3
    }
} finally {
    Disconnect-VIServer -Server $vi -Confirm:$false
}
