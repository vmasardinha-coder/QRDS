param(
  [string]$MainRepo = (Resolve-Path (Join-Path $PSScriptRoot "..")),
  [Parameter(Mandatory=$true)][string]$RuntimeRepo,
  [int]$IntervalSeconds = 120,
  [switch]$Once
)

$ErrorActionPreference = "Stop"
$env:MT5_READ_ONLY = "true"
$env:SHADOW_ONLY = "true"
$env:PAPER_CALCULATION = "true"
$env:NO_ORDER_SEND = "true"
$env:ORDERS = "0"
$env:REAL_CAPITAL = "0"
$env:ENGINE_FEED = "false"
$env:NO_RETUNE = "true"
$env:NO_BACKFILL = "true"

$healthDir = Join-Path $env:LOCALAPPDATA "QRDS"
$healthPath = Join-Path $healthDir "H31_LOCAL_HEALTH.json"
New-Item -ItemType Directory -Force -Path $healthDir | Out-Null

function Set-H31LocalHealth {
  param(
    [Parameter(Mandatory=$true)][string]$State,
    [Parameter(Mandatory=$true)][string]$Market,
    [string]$Detail = "",
    [Nullable[int]]$RunnerExitCode = $null
  )
  $now = [DateTimeOffset]::Now
  $obj = [ordered]@{
    schema = "gate_btc.b3.h31.local_health.v1"
    state = $State
    agent_alive = $true
    market = $Market
    updated_at_local = $now.ToString("o")
    updated_at_utc = $now.UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
    next_check_seconds = $IntervalSeconds
    mt5_read_only = $true
    shadow_only = $true
    no_order_send = $true
    orders = 0
    real_capital = 0
    engine_feed = $false
    runner_exit_code = $RunnerExitCode
    detail = $Detail
  }
  $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $healthPath -Encoding UTF8
  $host.UI.RawUI.WindowTitle = "QRDS H31 | $State | MARKET $Market | $(Get-Date -Format 'HH:mm:ss')"
  Write-Host ("[{0}] H31={1} MARKET={2} {3}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $State, $Market, $Detail)
}

function Get-H31MarketState {
  $now = [DateTimeOffset]::Now
  if ($now.DayOfWeek -eq [DayOfWeek]::Saturday -or $now.DayOfWeek -eq [DayOfWeek]::Sunday) { return "CLOSED" }
  $sessionStart = Get-Date -Hour 8 -Minute 55 -Second 0
  $sessionEnd = Get-Date -Hour 18 -Minute 30 -Second 0
  if ($now.LocalDateTime -lt $sessionStart -or $now.LocalDateTime -gt $sessionEnd) { return "CLOSED" }
  return "OPEN"
}

function Invoke-H31Checkpoint {
  $market = Get-H31MarketState
  if ($market -eq "CLOSED") {
    Set-H31LocalHealth -State "AGENT_ALIVE" -Market "CLOSED" -Detail "MARKET_CLOSED_NO_SCIENTIFIC_CHECKPOINT"
    return
  }

  Set-H31LocalHealth -State "CHECKING" -Market "OPEN" -Detail "RUNNING_READ_ONLY_MT5_CHECKPOINT"
  Push-Location $MainRepo
  try {
    $canonical = Join-Path $RuntimeRepo "runtime/ledgers/b3_h31_prospective"
    $shadow = Join-Path $RuntimeRepo "runtime/ledgers/b3_h31_shadow_paper"
    & python "tools/gate_btc_b3_h31_intraday_shadow.py" --canonical-dir $canonical --shadow-dir $shadow
    $rc = $LASTEXITCODE
    if ($rc -ne 0 -and $rc -ne 2) { throw "H31 runner exit code $rc" }

    Push-Location $RuntimeRepo
    try {
      git add runtime/ledgers/b3_h31_shadow_paper
      git diff --cached --quiet
      if ($LASTEXITCODE -ne 0) {
        $stamp = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        git commit -m "Append H31 MT5 intraday shadow checkpoint $stamp"
        git pull --rebase origin gate-btc-runtime
        git push origin HEAD:gate-btc-runtime
      }
    }
    finally { Pop-Location }
    Set-H31LocalHealth -State "ACTIVE" -Market "OPEN" -Detail "READ_ONLY_MT5_CHECKPOINT_OK" -RunnerExitCode $rc
  }
  finally { Pop-Location }
}

if ($Once) {
  try {
    Invoke-H31Checkpoint
    exit 0
  }
  catch {
    Set-H31LocalHealth -State "DEGRADED" -Market (Get-H31MarketState) -Detail $_.Exception.Message
    Write-Error $_
    exit 1
  }
}

while ($true) {
  try {
    Invoke-H31Checkpoint
  }
  catch {
    Set-H31LocalHealth -State "DEGRADED" -Market (Get-H31MarketState) -Detail $_.Exception.Message
  }
  Start-Sleep -Seconds $IntervalSeconds
}
