Set-Location $PSScriptRoot\..
& git.exe add -A
& git.exe commit -F .git/COMMIT_EDITMSG_TMP
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& git.exe push origin master
