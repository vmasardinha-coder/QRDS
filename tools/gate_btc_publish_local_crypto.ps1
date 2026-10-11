[CmdletBinding()]
param(
    [string]$CodeRoot = 'C:\actions-runner\qrds-local-shadow\code_canonical',
    [string]$RuntimeRepo = 'C:\actions-runner\qrds-local-shadow\runtime_canonical',
    [string]$LocalRoot = "$env:LOCALAPPDATA\GATE_BTC_CRYPTO_FULL_SOURCE_V1",
    [string]$Python = "$env:LOCALAPPDATA\GATE_BTC_D50_AUTOPILOT_V2\runtime\venv\Scripts\python.exe",
    [switch]$ValidateOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$Mutex = New-Object System.Threading.Mutex($false, 'Global\QRDS_CRYPTO_FULL_SOURCE_V1')
$Acquired = $false
$Worktree = $null
function Run-Git([string]$Repo, [string[]]$Arguments) {
    & git -C $Repo @Arguments
    if ($LASTEXITCODE -ne 0) { throw "GIT_FAILED=$($Arguments[0])" }
}
function Run-Python([string[]]$Arguments) {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "CRYPTO_SOURCE_TOOL_FAILED=$($Arguments[0])" }
}
try {
    try { $Acquired = $Mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $Acquired = $true }
    if (-not $Acquired) { Write-Host 'CRYPTO_FULL_SOURCE=ALREADY_RUNNING'; exit 0 }
    $Capture = Join-Path $CodeRoot 'tools\gate_btc_factory\crypto_forward_public_capture.py'
    $Publish = Join-Path $CodeRoot 'tools\gate_btc_factory\crypto_full_local_publication.py'
    $Families = Join-Path $CodeRoot 'tools\gate_btc_factory\crypto_family_state_runtime.py'
    foreach ($Path in @($Python,$Capture,$Publish,$Families)) {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "REQUIRED_FILE_MISSING=$Path" }
    }
    if ($ValidateOnly) {
        Run-Python @($Publish,'--help')
        Write-Host 'CRYPTO_FULL_SOURCE_CONFIG=PASS; CAPTURE_EXECUTED=False'
        exit 0
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $LocalRoot 'spool') | Out-Null
    Start-Transcript -Path (Join-Path $LocalRoot 'LATEST.log') -Force | Out-Null
    $Packet = Join-Path $LocalRoot ('spool\'+[datetime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.json')
    # One fresh source observation per run; no retrospective pairing or economic import.
    Run-Python @($Capture,'--full-source-contract','--out',$Packet)
    Run-Git $RuntimeRepo @('fetch','origin','gate-btc-runtime')
    $Worktree = Join-Path (Split-Path -Parent $RuntimeRepo) ('crypto_'+[guid]::NewGuid().ToString('N').Substring(0,8))
    Run-Git $RuntimeRepo @('worktree','add','--detach',$Worktree,'origin/gate-btc-runtime')
    for ($Attempt=1; $Attempt -le 4; $Attempt++) {
        if ($Attempt -gt 1) {
            Run-Git $Worktree @('fetch','origin','gate-btc-runtime')
            # Only this disposable detached publication worktree is rebuilt.
            # The incumbent runtime checkout and all local ledgers are untouched.
            Run-Git $Worktree @('reset','--hard','origin/gate-btc-runtime')
        }
        $Root = Join-Path $Worktree 'runtime\factory_sources\crypto_forward'
        Run-Python @($Publish,'--root',$Root,'--packet',$Packet)
        Run-Python @($Families,'--original-admission',(Join-Path $Root 'SOURCE_ADMISSION.json'),'--accessible-admission',(Join-Path $Root 'ACCESSIBLE_SOURCE_ADMISSION.json'),'--out',(Join-Path $Root 'FAMILY_STATES.json'))
        Run-Git $Worktree @('add','runtime/factory_sources/crypto_forward/full_local','runtime/factory_sources/crypto_forward/FULL_LOCAL_LATEST.json','runtime/factory_sources/crypto_forward/SOURCE_ADMISSION.json','runtime/factory_sources/crypto_forward/FAMILY_STATES.json')
        Run-Git $Worktree @('-c','user.name=gate-btc-research-bot','-c','user.email=gate-btc-research-bot@users.noreply.github.com','commit','-m','Append live full-contract crypto source proof; no economic rows')
        & git -C $Worktree push origin HEAD:gate-btc-runtime
        if ($LASTEXITCODE -eq 0) {
            Write-Host 'CRYPTO_FULL_SOURCE=PUBLISHED; ECONOMIC_ROWS_APPENDED=0; ORDERS=0; CAPITAL=0'
            Run-Git $RuntimeRepo @('worktree','remove',$Worktree)
            $Worktree = $null
            exit 0
        }
    }
    throw 'CRYPTO_SOURCE_PUSH_RETRIES_EXHAUSTED'
}
finally {
    try { Stop-Transcript | Out-Null } catch {}
    if ($Acquired) { $Mutex.ReleaseMutex() }
    $Mutex.Dispose()
}
