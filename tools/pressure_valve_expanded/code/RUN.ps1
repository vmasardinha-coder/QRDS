param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference='Stop'
$Python='C:\actions-runner\_work\_tool\Python\3.11.9\x64\python.exe'
$Now=[TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,'E. South America Standard Time')
$Stage=if($Now.Hour -ge 19){'evening'}else{'morning'}
$LogDir=Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log=Join-Path $LogDir ($Now.ToString('yyyy-MM-dd')+'_'+$Stage+'.log')
"START $($Now.ToString('o')) stage=$Stage" | Add-Content $Log
& $Python (Join-Path $PSScriptRoot 'pressure_valve_expanded.py') capture --root $Root --stage $Stage 2>&1 | Tee-Object -FilePath $Log -Append
$Code=$LASTEXITCODE
"END exit=$Code" | Add-Content $Log
exit $Code
