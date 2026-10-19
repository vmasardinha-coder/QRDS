[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$InstallRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Join-Path $InstallRoot "project\GATE_BTC_SPRINT0_V2_20260731"
$StateRoot = Join-Path $InstallRoot "state"
$VenvPython = Join-Path $InstallRoot "runtime\venv\Scripts\python.exe"
$Downloads = Join-Path ([Environment]::GetFolderPath("UserProfile")) "Downloads"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Logs = Join-Path $StateRoot "logs"
$Report = Join-Path $Logs "GATE_BTC_D50_DAILY_$Timestamp.txt"
$LatestReport = Join-Path $Downloads "GATE_BTC_D50_DAILY_LATEST.txt"
$MutexName = "Global\GATE_BTC_OKX_COLLECTION_MUTEX_V1"
$ExistingTaskName = "GATE_BTC_DAILY_DATA_QUALIFICATION"
$Status = "FAIL"
$Stage = "INITIALIZATION"
$Lines = New-Object System.Collections.Generic.List[string]
$CollectionMutex = $null
$MutexAcquired = $false
$MutexWaitSeconds = 0
$ExistingTaskWaitSeconds = 0

function Add-Line {
    param([object]$Value)
    $Text = [string]$Value
    $Lines.Add($Text)
    Write-Host $Text
}

function Invoke-Native {
    param([string]$Executable, [string[]]$Arguments, [string]$Label)
    Add-Line "STEP_BEGIN=$Label"
    $OldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Executable @Arguments 2>&1 | ForEach-Object { Add-Line $_ }
    $Code = $LASTEXITCODE
    $ErrorActionPreference = $OldPreference
    Add-Line "STEP_END=$Label EXIT_CODE=$Code"
    if ($Code -ne 0) { throw "$Label returned exit code $Code" }
}

function Enter-CollectionMutex {
    $script:CollectionMutex = New-Object System.Threading.Mutex -ArgumentList $false, $MutexName
    $Timer = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $script:MutexAcquired = $script:CollectionMutex.WaitOne([TimeSpan]::FromHours(6))
    }
    catch [System.Threading.AbandonedMutexException] {
        $script:MutexAcquired = $true
        Add-Line "MUTEX_RECOVERY=ABANDONED_OWNER_RECOVERED"
    }
    finally {
        $Timer.Stop()
        $script:MutexWaitSeconds = [math]::Round($Timer.Elapsed.TotalSeconds, 3)
    }
    if (-not $script:MutexAcquired) {
        throw "Tempo limite aguardando a outra coleta; nenhuma consulta paralela foi iniciada."
    }
    Add-Line "COLLECTION_MUTEX=$MutexName"
    Add-Line "MUTEX_WAIT_SECONDS=$script:MutexWaitSeconds"
    Add-Line "PARALLEL_OKX_COLLECTION=False"
}

function Exit-CollectionMutex {
    if ($script:MutexAcquired -and $null -ne $script:CollectionMutex) {
        try { $script:CollectionMutex.ReleaseMutex() } catch { }
    }
    if ($null -ne $script:CollectionMutex) {
        $script:CollectionMutex.Dispose()
    }
    $script:MutexAcquired = $false
}

function Wait-ExistingTaskIdle {
    $Timer = [System.Diagnostics.Stopwatch]::StartNew()
    $Deadline = (Get-Date).AddHours(6)
    while ($true) {
        $Matches = @(Get-ScheduledTask -TaskName $ExistingTaskName -ErrorAction SilentlyContinue)
        if ($Matches.Count -eq 0) { break }
        if ($Matches.Count -ne 1) {
            throw "Mais de uma tarefa antiga encontrada; nao foi iniciada coleta concorrente."
        }
        if ([string]$Matches[0].State -ne "Running") { break }
        if ((Get-Date) -ge $Deadline) {
            throw "Tempo limite aguardando a coleta antiga ja em execucao."
        }
        Start-Sleep -Seconds 15
    }
    $Timer.Stop()
    $script:ExistingTaskWaitSeconds = [math]::Round($Timer.Elapsed.TotalSeconds, 3)
    Add-Line "EXISTING_TASK_IDLE_WAIT_SECONDS=$script:ExistingTaskWaitSeconds"
}

try {
    New-Item -ItemType Directory -Force -Path $Downloads, $Logs | Out-Null
    if (-not (Test-Path -LiteralPath $VenvPython)) { throw "Runtime privado ausente; reinstale o pacote." }

    $Stage = "WAIT_EXISTING_TASK_IDLE"
    Wait-ExistingTaskIdle

    $Stage = "WAIT_SHARED_COLLECTION_MUTEX"
    Enter-CollectionMutex

    $Stage = "OFFICIAL_OKX_EXPORT"
    $RawZip = Join-Path $StateRoot "delta_walk_forward_outputs_v12_prereg_v2_latest.zip"
    Invoke-Native $VenvPython @((Join-Path $ProjectRoot "implementation\delta\scripts\00_run_delta_v12_prereg_v2.py"), "--output-zip", $RawZip) "EXPORT_OFFICIAL_20_OF_20"

    $Stage = "FAIL_CLOSED_GATE"
    Invoke-Native $VenvPython @((Join-Path $ProjectRoot "source\ingestion_guard_v2.py"), "--root", $ProjectRoot, "--require-pass") "VALIDATE_GATE"

    $Stage = "REPLAY_AND_APPEND"
    $ReplayDir = Join-Path $ProjectRoot "outputs\candidate_replay_real"
    Invoke-Native $VenvPython @(
        (Join-Path $ProjectRoot "source\d50_candidate_engine.py"),
        "--baseline-root", (Join-Path $ProjectRoot "implementation\delta"),
        "--output-dir", $ReplayDir,
        "--ohlc", (Join-Path $ProjectRoot "implementation\delta\data\delta_ohlc_daily.csv"),
        "--funding", (Join-Path $ProjectRoot "implementation\delta\data\delta_funding_events.csv")
    ) "RUN_REAL_REPLAY"
    Invoke-Native $VenvPython @(
        (Join-Path $ProjectRoot "source\update_d50_prospective_v2.py"),
        "--root", $ProjectRoot,
        "--state-dir", $StateRoot,
        "--gate-anchor-utc", "2026-07-31T16:59:39.790677+00:00"
    ) "APPEND_ONLY_ADMISSIBLE_BAR"

    # D50_POSITION_AUDIT_V1
    # Reporting/audit only. Does not feed or modify the economic engine.
    try {
        Invoke-Native $VenvPython @(
            (Join-Path $InstallRoot "audit\d50_position_audit_v1.py"),
            $ReplayDir,
            $StateRoot,
            $Downloads
        ) "D50_POSITION_AUDIT_V1"
        Add-Line "POSITION_AUDIT=PASS"

        # GATE_BTC_GOVERNANCE_MASTER_V1
        try {
            $GovernanceOutput = & $VenvPython `
                (Join-Path $InstallRoot "governance\gate_btc_governance_master_v1.py") `
                $InstallRoot `
                $ProjectRoot `
                $StateRoot `
                $Downloads
            $GovernanceExitCode = $LASTEXITCODE
            foreach ($GovernanceLine in $GovernanceOutput) {
                Add-Line ([string]$GovernanceLine)
            }

            if ($GovernanceExitCode -eq 0) {
                Add-Line "GOVERNANCE_MASTER=PASS"
            }
            else {
                Add-Line "GOVERNANCE_MASTER=WARN"
            }
        }
        catch {
            Add-Line "GOVERNANCE_MASTER=WARN"
            Add-Line "GOVERNANCE_MASTER_ERROR=$($_.Exception.Message)"
            Add-Line "GOVERNANCE_MASTER_ENGINE_IMPACT=False"
        }
    }
    catch {
        Add-Line "POSITION_AUDIT=WARN_FAIL_ISOLATED"
        Add-Line "POSITION_AUDIT_ERROR=$($_.Exception.Message)"
        Add-Line "POSITION_AUDIT_ENGINE_IMPACT=False"
    }

    $Prospective = Get-Content -Raw -LiteralPath (Join-Path $StateRoot "D50_PROSPECTIVE_STATUS_V2.json") | ConvertFrom-Json
    $Observation = [int]$Prospective.paired_prospective_observations
    $Status = "PASS_DAILY_UPDATE"

    if ([bool]$Prospective.checkpoint_due) {
        $Marker = Join-Path $StateRoot ("checkpoint_{0:D3}_emitted.txt" -f $Observation)
        if (-not (Test-Path -LiteralPath $Marker)) {
            $Stage = "CREATE_CHECKPOINT_PACK"
            $CheckpointRoot = Join-Path $StateRoot ("checkpoint_{0:D3}_{1}" -f $Observation, $Timestamp)
            New-Item -ItemType Directory -Force -Path $CheckpointRoot | Out-Null
            Copy-Item -LiteralPath (Join-Path $StateRoot "d50_prospective_observations_v2.csv") -Destination $CheckpointRoot -Force
            Copy-Item -LiteralPath (Join-Path $StateRoot "d50_prospective_summary_v2.csv") -Destination $CheckpointRoot -Force
            Copy-Item -LiteralPath (Join-Path $StateRoot "D50_PROSPECTIVE_STATUS_V2.json") -Destination $CheckpointRoot -Force
            Copy-Item -LiteralPath (Join-Path $StateRoot "VOL20_ONE_TIME_GATE_V2.json") -Destination $CheckpointRoot -Force -ErrorAction SilentlyContinue
            Copy-Item -LiteralPath (Join-Path $ProjectRoot "outputs\INGESTION_GATE_STATUS_V2.json") -Destination $CheckpointRoot -Force
            Copy-Item -LiteralPath $RawZip -Destination $CheckpointRoot -Force
            Copy-Item -Path (Join-Path $ReplayDir "*") -Destination $CheckpointRoot -Recurse -Force
            $CheckpointZip = Join-Path $Downloads ("GATE_BTC_D50_CHECKPOINT_OBS{0:D3}_{1}.zip" -f $Observation, $Timestamp)
            Compress-Archive -Path (Join-Path $CheckpointRoot "*") -DestinationPath $CheckpointZip -CompressionLevel Optimal
            "EMITTED=$(Get-Date -Format o)`nZIP=$CheckpointZip" | Set-Content -LiteralPath $Marker -Encoding UTF8
            Add-Line "CHECKPOINT_PACK=$CheckpointZip"
        }
    }
}
catch {
    Add-Line "ERROR_TYPE=$($_.Exception.GetType().FullName)"
    Add-Line "ERROR=$($_.Exception.Message)"
    Add-Line "STACK=$($_.ScriptStackTrace)"
}
finally {
    New-Item -ItemType Directory -Force -Path $Downloads, $Logs | Out-Null
    $ProspectivePath = Join-Path $StateRoot "D50_PROSPECTIVE_STATUS_V2.json"
    $ObservationText = "UNAVAILABLE"
    $NextCheckpoint = "UNAVAILABLE"
    if (Test-Path -LiteralPath $ProspectivePath) {
        $Snapshot = Get-Content -Raw -LiteralPath $ProspectivePath | ConvertFrom-Json
        $ObservationText = [string]$Snapshot.paired_prospective_observations
        $NextCheckpoint = [string]$Snapshot.next_checkpoint
    }
    $Summary = @(
        "GATE BTC D50 - DAILY AUTOPILOT",
        "FINISHED=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')",
        "STATUS=$Status",
        "STAGE_REACHED=$Stage",
        "COLLECTION_MUTEX=$MutexName",
        "MUTEX_WAIT_SECONDS=$MutexWaitSeconds",
        "EXISTING_TASK_IDLE_WAIT_SECONDS=$ExistingTaskWaitSeconds",
        "PARALLEL_OKX_COLLECTION_ALLOWED=False",
        "PROSPECTIVE_OBSERVATIONS=$ObservationText",
        "NEXT_CHECKPOINT=$NextCheckpoint",
        "HISTORICAL_BACKFILL_COUNTS_AS_PROSPECTIVE=False",
        "RESEARCH_ONLY=True",
        "ORDERS=0",
        "CAPITAL=0",
        "KEEP=GATE_BTC_D50_DAILY_LATEST.txt",
        "MAY_DELETE=older dated logs if manually copied",
        "NEXT_USER_ACTION=NONE_UNTIL_CHECKPOINT_PACK_IS_CREATED",
        "",
        "=== COMPLETE OUTPUT ==="
    ) + $Lines
    $Summary | Set-Content -LiteralPath $Report -Encoding UTF8
    Copy-Item -LiteralPath $Report -Destination $LatestReport -Force
    Exit-CollectionMutex
}

if ($Status -ne "PASS_DAILY_UPDATE") { exit 1 }
exit 0


