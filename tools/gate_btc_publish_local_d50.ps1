[CmdletBinding()]
param(
    [string]$CodeRoot = 'C:\actions-runner\qrds-local-shadow\code_canonical',
    [string]$RuntimeRepo = 'C:\actions-runner\qrds-local-shadow\runtime_canonical',
    [string]$LocalRoot = "$env:LOCALAPPDATA\GATE_BTC_D50_AUTOPILOT_V2",
    [string]$QualificationRoot = 'C:\GATE_BTC_PROJECT\RUNTIME\LEGACY_DATA_COLLECTION_V1\crypto_decision_lab\gate_btc_runtime',
    [switch]$ValidateOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$Python = Join-Path $LocalRoot 'runtime\venv\Scripts\python.exe'
$Tool = Join-Path $CodeRoot 'tools\gate_btc_d50_local_mirror.py'
$Log = Join-Path $LocalRoot 'logs\D50_RUNTIME_MIRROR_LATEST.log'
$Mutex = New-Object System.Threading.Mutex($false, 'Global\QRDS_D50_REPORTING_MIRROR_V1')
$Acquired = $false
$Worktree = $null
function Run-Git([string]$Repo, [string[]]$Arguments) {
    & git -C $Repo @Arguments
    if ($LASTEXITCODE -ne 0) { throw "GIT_FAILED=$($Arguments[0])" }
}
function Run-Python([string[]]$Arguments) {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "REPORTING_TOOL_FAILED=$($Arguments[0])" }
}
try {
    try { $Acquired = $Mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $Acquired = $true }
    if (-not $Acquired) { throw 'D50_REPORTING_MIRROR_ALREADY_RUNNING' }
    foreach ($Path in @($Python,$Tool,(Join-Path $QualificationRoot 'qualification_status.json'))) {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "REQUIRED_FILE_MISSING=$Path" }
    }
    if ($ValidateOnly) {
        Run-Python @($Tool,'--help')
        Write-Host 'D50_REPORTING_PUBLISHER_CONFIG=PASS; COLLECTION_EXECUTED=False'
        exit 0
    }
    Start-Transcript -Path $Log -Force | Out-Null
    Run-Git $RuntimeRepo @('fetch','origin','gate-btc-runtime')
    # A short path also works on Windows installations without long paths enabled.
    $Worktree = Join-Path (Split-Path -Parent $RuntimeRepo) ('mirror_' + [guid]::NewGuid().ToString('N').Substring(0,8))
    Run-Git $RuntimeRepo @('worktree','add','--detach',$Worktree,'origin/gate-btc-runtime')
    $Runtime = Join-Path $Worktree 'runtime'
    $State = Join-Path $Runtime 'GATE_BTC_REPORTING_CURRENT_STATE.json'
    Run-Python @($Tool,'--local-root',$LocalRoot,'--qualification-root',$QualificationRoot,'--runtime-root',$Runtime,'--output-root',$Runtime)
    Run-Python @((Join-Path $CodeRoot 'tools\gate_btc_reporting_current_state.py'),'--runtime-root',$Runtime,'--output',$State)
    Run-Python @((Join-Path $CodeRoot 'tools\gate_btc_reporting_operational_overlay.py'),'--runtime-root',$Runtime,'--state',$State)
    Run-Python @((Join-Path $CodeRoot 'tools\gate_btc_reporting_inventory.py'),'--runtime-root',$Runtime,'--state',$State)
    Run-Python @((Join-Path $CodeRoot 'tools\gate_btc_executive_track_catalog.py'),'--state',$State,'--artifact-root',(Join-Path $Worktree 'artifacts'),'--requirements',(Join-Path $CodeRoot 'tools\gate_btc_executive_reporting_requirements.json'))
    Run-Python @((Join-Path $CodeRoot 'tools\gate_btc_shadow_executive.py'),'--state',$State,'--output-dir',(Join-Path $Runtime 'executive'))
    Run-Git $Worktree @('add','runtime/GATE_BTC_MEASUREMENT_STATUS.json','runtime/ledgers/d50/STATUS.json','runtime/ledgers/d50/LOCAL_MIRROR_AUDIT.json','runtime/GATE_BTC_REPORTING_CURRENT_STATE.json')
    $ReportingDate = (Get-Content -LiteralPath $State -Raw | ConvertFrom-Json).reporting_date_utc
    Run-Git $Worktree @('add','runtime/executive/SHADOW_EXECUTIVE_LATEST.json','runtime/executive/SHADOW_EXECUTIVE_LATEST.md',"runtime/executive/SHADOW_EXECUTIVE_$ReportingDate.json","runtime/executive/SHADOW_EXECUTIVE_$ReportingDate.md")
    & git -C $Worktree diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Write-Host 'D50_REPORTING_MIRROR=NO_CHANGE'; exit 0 }
    Run-Git $Worktree @('-c','user.name=gate-btc-reporting-bot','-c','user.email=gate-btc-reporting-bot@users.noreply.github.com','commit','-m','Reconcile existing local D50 reporting evidence')
    # Rebase only the reporting commit. A conflict stops publication and retains
    # this isolated worktree for inspection; it never touches the local ledger.
    for ($Attempt=1; $Attempt -le 4; $Attempt++) {
        Run-Git $Worktree @('fetch','origin','gate-btc-runtime')
        & git -C $Worktree rebase origin/gate-btc-runtime
        if ($LASTEXITCODE -ne 0) {
            & git -C $Worktree rebase --abort
            throw 'REPORTING_CONFLICT_REVIEW_REQUIRED'
        }
        & git -C $Worktree push origin HEAD:gate-btc-runtime
        if ($LASTEXITCODE -eq 0) {
            Write-Host 'D50_REPORTING_MIRROR=PUBLISHED; ECONOMIC_ROWS_MUTATED=0; ORDERS=0; CAPITAL=0'
            Run-Git $RuntimeRepo @('worktree','remove',$Worktree)
            $Worktree = $null
            exit 0
        }
    }
    throw 'REPORTING_PUSH_RETRIES_EXHAUSTED'
}
finally {
    try { Stop-Transcript | Out-Null } catch {}
    if ($Acquired) { $Mutex.ReleaseMutex() }
    $Mutex.Dispose()
}
