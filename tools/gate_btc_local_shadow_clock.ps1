[CmdletBinding()]
param([switch]$CalendarPreflightOnly,[string]$CalendarDate='')
$ErrorActionPreference='Stop'
$Root='C:\actions-runner\qrds-local-shadow'
$Py='C:\actions-runner\_work\_tool\Python\3.11.9\x64\python.exe'
$Mt5='C:\Program Files\Hantec Markets MetaTrader 5\terminal64.exe'
$Code=Join-Path $Root 'code_canonical'
$Runtime=Join-Path $Root 'runtime_canonical'
$LogDir=Join-Path $Root 'logs'
$SpoolRoot=Join-Path $Root 'spool'
$H31Spool=Join-Path $SpoolRoot 'b3_h31_shadow_paper'
$H1Spool=Join-Path $SpoolRoot 'b3_h1_inspired_challengers'
$Log=Join-Path $LogDir ((Get-Date -Format 'yyyy-MM-dd')+'.log')

function Log([string]$m){ Add-Content -Path $Log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff') | $m" -Encoding UTF8 }

# Preflight dates are read-only; real execution always uses the local session date.
$GuardDate = if($CalendarPreflightOnly -and $CalendarDate){$CalendarDate}else{Get-Date -Format 'yyyy-MM-dd'}
$CalendarTool=Join-Path $Code 'tools\gate_btc_b3_intraday_calendar_guard.py'
$CalendarJson = & $Py $CalendarTool --date $GuardDate
if($LASTEXITCODE -ne 0){throw 'CALENDAR_GUARD_FAILED'}
$Calendar=$CalendarJson | ConvertFrom-Json
if($Calendar.schema -ne 'qrds.b3.intraday_calendar_guard.v1' -or $Calendar.date -ne $GuardDate -or $Calendar.eligible_observation_increment -ne 0){throw 'CALENDAR_GUARD_INVALID'}
if($CalendarPreflightOnly){Write-Output $CalendarJson;exit 0}
if($Calendar.decision -eq 'SKIP_KNOWN_NON_SESSION'){
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  Log ('LOCAL_INTRADAY_NON_SESSION=' + $Calendar.reason + '; CREDIT=0; ORDERS=0; CAPITAL=0')
  exit 0
}
if($Calendar.decision -ne 'CONTINUE_EXISTING_SOURCE_GUARDS'){throw 'CALENDAR_GUARD_UNKNOWN_DECISION'}

New-Item -ItemType Directory -Force -Path $LogDir,$SpoolRoot | Out-Null
try{
  Log 'LOCAL_INTRADAY_SUPERVISOR_START'
  if(-not (Test-Path $Py)){throw 'PYTHON_NOT_FOUND'}
  if(-not (Test-Path $Mt5)){throw 'MT5_TERMINAL_NOT_FOUND'}
  & $Py -c "import MetaTrader5 as m; ok=m.initialize(path=r'$Mt5'); print('MT5_INIT='+str(ok)); print('MT5_LAST_ERROR='+repr(m.last_error())); m.shutdown(); raise SystemExit(0 if ok else 93)" 2>&1 | ForEach-Object { Log "MT5 $($_)" }
  if($LASTEXITCODE -ne 0){throw "MT5_NOT_READY rc=$LASTEXITCODE"}
  Log 'MT5_LOCAL_READY=true'

  & $Py (Join-Path $Root 'sync_canonical_worktrees.py') 2>&1 | ForEach-Object { Log "SAFE_SYNC $($_)" }
  if($LASTEXITCODE -ne 0){throw "SAFE_SYNC_FAILED rc=$LASTEXITCODE"}
  Log "QRDS_MAIN_HEAD=$(& git -C $Code rev-parse HEAD)"
  Log "QRDS_RUNTIME_HEAD=$(& git -C $Runtime rev-parse HEAD)"

  $h31Source=Join-Path $Runtime 'runtime\ledgers\b3_h31_shadow_paper'
  $h1Source=Join-Path $Runtime 'runtime\ledgers\b3_h1_inspired_challengers'
  if(-not (Test-Path $H31Spool)){ if(Test-Path $h31Source){Copy-Item $h31Source $H31Spool -Recurse -Force}else{New-Item -ItemType Directory -Force -Path $H31Spool|Out-Null}; Log 'H31_SPOOL_READY=true' }
  if(-not (Test-Path $H1Spool)){ if(Test-Path $h1Source){Copy-Item $h1Source $H1Spool -Recurse -Force}else{New-Item -ItemType Directory -Force -Path $H1Spool|Out-Null}; Log 'H1_SPOOL_READY=true' }

  $h31='tools\gate_btc_b3_h31_intraday_bound_entrypoint.py'
  $h1=Join-Path $Root 'local_h1_opening_v2\run_h1.py'
  foreach($rel in @($h31,$h1)){
    $p=if([System.IO.Path]::IsPathRooted($rel)){$rel}else{Join-Path $Code $rel}
    if(-not (Test-Path $p)){throw "MISSING_BOUND_RUNNER $rel"}
    $txt=(Get-Content $p -Raw).ToLower(); $forbidden='order'+'_send'+'('
    if($txt.Contains($forbidden)){throw "FORBIDDEN_ORDER_API $rel"}
  }
  $bindingProbe = & $Py $h1 --deployment-check
  if($LASTEXITCODE -ne 0){throw 'H1_V2_DEPLOYMENT_CHECK_FAILED'}
  $binding = $bindingProbe | ConvertFrom-Json
  if($binding.deployment -ne 'H1_OPENING_V2' -or $binding.active_contract_today -ne 'contract_v2.json' -or $binding.syntax -ne 'PASS' -or $binding.runtime_ledger_touched -ne $false){throw 'H1_V2_BINDING_NOT_VERIFIED'}
  Log 'H1_V2_BINDING=PASS; CANONICAL_CREDIT=0'
  Log 'BOUND_RUNNERS_READY=true'
  Log 'SAFETY_SCAN=PASS'

  $canonical=Join-Path $Runtime 'runtime\ledgers\b3_h31_prospective'
  $start=(Get-Date).Date.AddHours(9)
  $stop=(Get-Date).Date.AddHours(11).AddMinutes(40)
  while((Get-Date) -lt $start){Start-Sleep -Seconds 10}
  while((Get-Date) -le $stop){
    Push-Location $Code
    try{
      & $Py $h31 --canonical-dir $canonical --shadow-dir $H31Spool 2>&1 | ForEach-Object {Log "H31 $($_)"}
      Log "H31_RC=$LASTEXITCODE"
      & $Py $h1 --runtime-dir $H1Spool 2>&1 | ForEach-Object {Log "H1C $($_)"}
      Log "H1C_RC=$LASTEXITCODE"
    } catch { Log "ITERATION_ERROR=$($_.Exception.Message)" } finally {Pop-Location}
    Start-Sleep -Seconds 30
  }
  Log 'LOCAL_INTRADAY_SUPERVISOR_STOP'
  exit 0
} catch {
  Log "FATAL_STAGE_ERROR=$($_.Exception.Message)"
  Log 'LOCAL_INTRADAY_SUPERVISOR_STOP_FATAL'
  exit 99
}

