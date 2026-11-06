param(
 [ValidateSet('WATCH_H1_H31','WATCH_VALVE','STATUS','AUTOPSIA_H1_H31','AUTOPSIA_VALVE','PORTAL')][string]$Action='STATUS',
 [switch]$Once
)
$ErrorActionPreference='Stop'
$Shadow='C:\actions-runner\qrds-local-shadow'
$Valve='C:\actions-runner\qrds-pressure-valve-shadow\spool\pressure_valves'
$Expanded='C:\actions-runner\qrds-pressure-valve-expanded'
function Read-Json($Path) {
 if(!(Test-Path $Path)){return $null}
 for($Attempt=0;$Attempt -lt 3;$Attempt++){
  try{return (Get-Content $Path -Raw | ConvertFrom-Json)}
  catch{if($Attempt -eq 2){throw};Start-Sleep -Milliseconds 100}
 }
}
function Task-Line($Name){
 try {
  $T=Get-ScheduledTask -TaskName $Name
  $I=Get-ScheduledTaskInfo -TaskName $Name
  Write-Host "$Name : $($T.State) | Last=$($I.LastRunTime.ToString('dd/MM HH:mm:ss')) | Result=$($I.LastTaskResult) | Next=$($I.NextRunTime.ToString('dd/MM HH:mm:ss'))"
 }catch{Write-Host "TASK ERROR $Name : $($_.Exception.Message)" -ForegroundColor Red}
}
function Show-Shadow {
 Write-Host '=== H1 / H31 ===' -ForegroundColor Cyan
 Task-Line 'QRDS-Local-Shadow-Clock'
 $A=Read-Json "$Shadow\spool\b3_h31_shadow_paper\INTRADAY_STATUS.json"
 if($A){
  Write-Host "H31 session=$($A.H31_INTRADAY_SESSION) | state=$($A.H31_INTRADAY_SHADOW_STATUS) | MT5=$($A.H31_MT5_READY)"
  Write-Host "WindowDone=$($A.H31_30M_WINDOW_COMPLETE) | trigger=$($A.H31_TRIGGER_STATE) | position=$($A.H31_PAPER_POSITION)"
  Write-Host "Sessions=$($A.H31_SHADOW_SESSIONS) | Trigger decisions=$($A.H31_SHADOW_TRIGGERED_SESSIONS) | Closed=$($A.H31_SHADOW_CLOSED_TRADES)"
  Write-Host "Updated=$($A.updated_at)"
 }
 $B=Read-Json "$Shadow\spool\b3_h1_inspired_challengers\STATUS.json"
 if($B){
  Write-Host "H1 session=$($B.session) | state=$($B.state) | MT5=$($B.mt5_ready)"
  foreach($C in $B.challengers.PSObject.Properties){Write-Host "$($C.Name) : $($C.Value.state)"}
  Write-Host "Updated=$($B.updated_at)"
 }
 Write-Host 'Shadow only. Orders real=0. Observe session and Updated.' -ForegroundColor DarkGray
}
function Show-Valve {
 Write-Host '=== VALVE LEGADO / AMPLIADO ===' -ForegroundColor Cyan
 Task-Line 'QRDS-Pressure-Valve-Shadow'
 Task-Line 'QRDS-Pressure-Valve-Expanded'
 foreach($P in @("$Valve\STATUS.json","$Expanded\STATUS.json")){
  $J=Read-Json $P
  if($J){Write-Host $P -ForegroundColor Yellow;$J|ConvertTo-Json -Depth 5|Write-Host}
 }
 $R=Read-Json "$Expanded\reports\INTRACYCLE_STATUS.json"
 if($R){Write-Host 'INTRACYCLE RESEARCH';$R|ConvertTo-Json -Depth 4|Write-Host}
 Write-Host 'Last consolidated session may be yesterday until 12:45. Session QA closes at 19:15.' -ForegroundColor DarkGray
}
switch($Action){
 'AUTOPSIA_H1_H31' {
  $Day=Get-Date -Format 'yyyy-MM-dd';$Out="$env:USERPROFILE\Downloads\QRDS_AUTOPSIA_FINAL_$Day.txt"
  "QRDS AUTOPSIA FINAL - $Day"|Set-Content $Out -Encoding UTF8
  "GERADO: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"|Add-Content $Out -Encoding UTF8
  '==================== SUPERVISOR LOG ===================='|Add-Content $Out -Encoding UTF8
  $Log="$Shadow\logs\$Day.log"
  if(Test-Path $Log){Get-Content $Log|Add-Content $Out -Encoding UTF8}
  foreach($Root in @("$Shadow\spool\b3_h31_shadow_paper","$Shadow\spool\b3_h1_inspired_challengers")){
   if(Test-Path $Root){Get-ChildItem $Root -File -Recurse|Sort-Object FullName|ForEach-Object{
    '------------------------------------------------------------'|Add-Content $Out -Encoding UTF8
    "FILE: $($_.FullName)"|Add-Content $Out -Encoding UTF8
    "LASTWRITE: $($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))"|Add-Content $Out -Encoding UTF8
    Get-Content $_.FullName -Raw|Add-Content $Out -Encoding UTF8
   }}
  }
  Write-Host "AUTOPSIA GERADA: $Out" -ForegroundColor Green
 }
 'AUTOPSIA_VALVE' {
  $Day=Get-Date -Format 'yyyy-MM-dd';$Out="$env:USERPROFILE\Downloads\QRDS_PRESSURE_VALVE_$Day.txt"
  "QRDS PRESSURE VALVE - $Day"|Set-Content $Out -Encoding UTF8
  "GERADO: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"|Add-Content $Out -Encoding UTF8
  '==================== TASK ===================='|Add-Content $Out -Encoding UTF8
  Get-ScheduledTaskInfo -TaskName 'QRDS-Pressure-Valve-Shadow'|Format-List LastRunTime,LastTaskResult,NextRunTime|Out-String|Add-Content $Out -Encoding UTF8
  foreach($N in @(@('STATUS','STATUS.json'),@('SNAPSHOT','DAILY_SNAPSHOT.json'),@('ECONOMICS','ECONOMICS.json'))){
   "==================== $($N[0]) ===================="|Add-Content $Out -Encoding UTF8
   $P=Join-Path $Valve $N[1]
   if(Test-Path $P){Get-Content $P -Raw|Add-Content $Out -Encoding UTF8}
  }
  Write-Host "PRESSURE VALVE GERADO: $Out" -ForegroundColor Green
  Write-Host "Ampliado: pacote automatico em Downloads\QRDS_PRESSURE_VALVE_EXPANDED_$Day.zip; atualizado 12:45/19:15."
 }
 'PORTAL' {Invoke-Item "$Expanded\reports\INTRACYCLE.html"}
 default {
  do{
   if(!$Once){Clear-Host}
   Write-Host "QRDS LOCAL MONITOR - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
   try {
    if($Action -in @('WATCH_H1_H31','STATUS')){Show-Shadow}
    if($Action -in @('WATCH_VALVE','STATUS')){Show-Valve}
   }catch{Write-Host "READ ERROR: $($_.Exception.Message)" -ForegroundColor Red}
   if($Once -or $Action -eq 'STATUS'){break}
   Write-Host 'CTRL+C para sair. Refresh 15 segundos.' -ForegroundColor DarkGray
   Start-Sleep -Seconds 15
  }while($true)
 }
}
