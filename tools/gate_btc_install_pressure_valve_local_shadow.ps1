param(
    [string]$RepoRoot = "C:\actions-runner\qrds-pressure-valve-shadow\QRDS",
    [string]$LocalRoot = "C:\actions-runner\qrds-pressure-valve-shadow",
    [string]$TaskName = "QRDS-Pressure-Valve-Shadow",
    [string]$PythonExe = "python",
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"

$ForbiddenRoot = "C:\actions-runner\qrds-local-shadow"
$ForbiddenTask = "QRDS-Local-Shadow-Clock"
$resolvedLocal = [System.IO.Path]::GetFullPath($LocalRoot).TrimEnd('\')
$resolvedForbidden = [System.IO.Path]::GetFullPath($ForbiddenRoot).TrimEnd('\')
if ($resolvedLocal.Equals($resolvedForbidden, [System.StringComparison]::OrdinalIgnoreCase) -or
    $resolvedLocal.StartsWith($resolvedForbidden + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "ISOLATION_FAIL: Pressure Valve root cannot be under H1/H31 root"
}
if ($TaskName -eq $ForbiddenTask) {
    throw "ISOLATION_FAIL: Pressure Valve task cannot replace H1/H31 task"
}

$collector = Join-Path $RepoRoot "tools\gate_btc_2_pressure_valve_local_shadow.py"
$config = Join-Path $RepoRoot "artifacts\gate_btc_2\PRESSURE_VALVE_LOCAL_SHADOW_CONFIG_20260922.json"
if (-not (Test-Path $collector)) { throw "COLLECTOR_NOT_FOUND: $collector" }
if (-not (Test-Path $config)) { throw "CONFIG_NOT_FOUND: $config" }

New-Item -ItemType Directory -Force -Path $LocalRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $LocalRoot "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $LocalRoot "spool\pressure_valves\ledger") | Out-Null

$arg = ('"{0}" --config "{1}" --root "{2}"' -f $collector, $config, $LocalRoot)
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $arg -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At "12:35"
$trigger.DaysInterval = 1

$params = @{
    ExecutionTimeLimit = (New-TimeSpan -Hours 2)
    MultipleInstances = "IgnoreNew"
    AllowStartIfOnBatteries = $true
    DontStopIfGoingOnBatteries = $true
    Hidden = $true
    StartWhenAvailable = $true
}
$cmd = Get-Command New-ScheduledTaskSettingsSet -ErrorAction Stop
if ($cmd.Parameters.ContainsKey("UseUnifiedSchedulingEngine")) {
    $params.UseUnifiedSchedulingEngine = $true
}
$settings = New-ScheduledTaskSettingsSet @params
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

$hTask = Get-ScheduledTask -TaskName $ForbiddenTask -ErrorAction SilentlyContinue
$pvTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if ($pvTask.TaskName -eq $ForbiddenTask) { throw "ISOLATION_FAIL_TASK_COLLISION" }

$result = [ordered]@{
    schema = "qrds.pressure_valve.local_task_install.v1"
    installed_at = (Get-Date).ToString("o")
    task = $TaskName
    local_root = $resolvedLocal
    repo_root = $RepoRoot
    schedule_local = "12:35 daily; collector itself rejects weekends/pre-D0/pre-window"
    h1_h31_task_present = [bool]($null -ne $hTask)
    h1_h31_task_name = $ForbiddenTask
    h1_h31_task_mutated = $false
    separate_task = $true
    separate_root = $true
    separate_spool = $true
    separate_ledger = $true
    MT5_READ_ONLY = $true
    RESEARCH_ONLY = $true
    SHADOW_ONLY = $true
    ENGINE_FEED = $false
    ORDERS = 0
    REAL_CAPITAL = 0
    SCIENTIFIC_CREDIT = 0
}

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 3
    $result.started_now = $true
    $result.state_after_start = (Get-ScheduledTask -TaskName $TaskName).State.ToString()
} else {
    $result.started_now = $false
}

$result | ConvertTo-Json -Depth 5
