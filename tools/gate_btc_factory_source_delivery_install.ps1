[CmdletBinding()]
param([string]$CodeRoot='C:\actions-runner\qrds-local-shadow\code_canonical',
 [string]$RuntimeRepo='C:\actions-runner\qrds-local-shadow\runtime_canonical',
 [string]$Python='C:\Users\jsard\AppData\Local\Programs\Python\Python312\python.exe',
 [switch]$ValidateOnly)
$ErrorActionPreference='Stop'
$wrapper=Join-Path $CodeRoot 'tools\gate_btc_factory_source_delivery.ps1'
if(-not(Test-Path -LiteralPath $wrapper -PathType Leaf)){throw 'VERSIONED_SOURCE_WRAPPER_MISSING'}
$definitions=@(
 @{name='QRDS_FACTORY_BASIS_WINDOW_V1';mode='basis';slots=@(@{h=7;m=15},@{h=15;m=15},@{h=23;m=15});limit=65},
 @{name='QRDS_FACTORY_XAGENT_PRODUCERS_V1';mode='xagent-producers';slots=@(@{h=1;m=30},@{h=1;m=45},@{h=2;m=0});limit=25}
)
$identity=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$results=@()
foreach($d in $definitions){
 & $wrapper -Mode $d.mode -CodeRoot $CodeRoot -RuntimeRepo $RuntimeRepo -Python $Python -ValidateOnly
 if($LASTEXITCODE -ne 0){throw 'SOURCE_CONFIG_VALIDATION_FAILED'}
 $times=@();$triggers=@()
 foreach($slot in $d.slots){
  $utc=[datetime]::SpecifyKind([datetime]::UtcNow.Date.AddHours($slot.h).AddMinutes($slot.m),[DateTimeKind]::Utc)
  if($utc -le [datetime]::UtcNow){$utc=$utc.AddDays(1)}
  $local=$utc.ToLocalTime();$times+=$utc.ToString('o');$triggers+=New-ScheduledTaskTrigger -Daily -At $local
 }
 if(-not $ValidateOnly){
  $existing=Get-ScheduledTask -TaskName $d.name -ErrorAction SilentlyContinue
  if($existing){
   $backup=Join-Path $env:LOCALAPPDATA 'QRDS_FACTORY_SOURCE_DELIVERY\task_backups';New-Item -ItemType Directory -Force -Path $backup | Out-Null
   Export-ScheduledTask -TaskName $d.name | Set-Content -LiteralPath (Join-Path $backup ($d.name+'_'+[datetime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.xml')) -Encoding UTF8
  }
  $args='-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$wrapper+'" -Mode '+$d.mode+' -CodeRoot "'+$CodeRoot+'" -RuntimeRepo "'+$RuntimeRepo+'" -Python "'+$Python+'"'
  $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $args
  $principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
  $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes $d.limit) -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $d.name -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Description 'Prospective research source delivery only; immutable clocks, no orders/capital/outcomes.' -Force | Out-Null
 }
 $results+=@{task=$d.name;mode=$d.mode;first_future_triggers_utc=$times;installed=(-not $ValidateOnly);task_started=$false;orders=0;real_capital=0}
}
$results | ConvertTo-Json -Depth 5 -Compress
