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

function Invoke-H31Checkpoint {
  $now = [DateTimeOffset]::Now
  if ($now.DayOfWeek -eq [DayOfWeek]::Saturday -or $now.DayOfWeek -eq [DayOfWeek]::Sunday) { return }
  $sessionStart = Get-Date -Hour 8 -Minute 55 -Second 0
  $sessionEnd = Get-Date -Hour 18 -Minute 30 -Second 0
  if ($now.LocalDateTime -lt $sessionStart -or $now.LocalDateTime -gt $sessionEnd) { return }

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
  }
  finally { Pop-Location }
}

if ($Once) {
  Invoke-H31Checkpoint
  exit 0
}

while ($true) {
  Invoke-H31Checkpoint
  Start-Sleep -Seconds $IntervalSeconds
}
