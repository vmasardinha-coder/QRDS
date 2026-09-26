param()
$ErrorActionPreference = 'Stop'
$Repo = 'vmasardinha-coder/QRDS'
$Workflow = '.github/workflows/gate-btc-b3-h31-intraday-shadow.yml'
$Gh = 'C:\Program Files\GitHub CLI\gh.exe'
$Log = 'C:\actions-runner-qrds\h31-local-dispatch-clock.log'
function Log([string]$m) {
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K') $m"
  Add-Content -Path $Log -Value $line -Encoding UTF8
}
if (-not (Test-Path $Gh)) { throw 'GH_CLI_MISSING' }
$day = [int](Get-Date).DayOfWeek
if ($day -eq 0 -or $day -eq 6) { Log 'WEEKEND_NOOP'; exit 0 }
$today = (Get-Date).Date
$start = $today.AddHours(9)
$end = $today.AddHours(18).AddMinutes(55)
if ((Get-Date) -gt $end) { Log 'OUTSIDE_WINDOW_NOOP'; exit 0 }
Log 'CLOCK_START'
while ($true) {
  $now = Get-Date
  if ($now -gt $end) { Log 'CLOCK_END'; exit 0 }
  if ($now -lt $start) {
    $next = $start
  } else {
    $base = Get-Date -Date $now -Second 0
    $mod = $base.Minute % 5
    if ($mod -eq 0 -and $now.Second -le 10) { $next = $base }
    else { $next = $base.AddMinutes($(if($mod -eq 0){5}else{5-$mod})) }
  }
  if ($next -gt $end) { Log 'CLOCK_END'; exit 0 }
  $sleep = [math]::Max(0, [int][math]::Ceiling(($next-(Get-Date)).TotalSeconds))
  if ($sleep -gt 0) { Start-Sleep -Seconds $sleep }
  & $Gh workflow run $Workflow --repo $Repo --ref main
  $rc = $LASTEXITCODE
  Log "DISPATCH slot=$($next.ToString('HH:mm')) rc=$rc"
  Start-Sleep -Seconds 15
}
