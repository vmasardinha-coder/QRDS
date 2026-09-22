param(
    [string]$TaskName = "QRDS-Local-Shadow-Clock",
    [int]$ExecutionHours = 72,
    [switch]$StartAfterRepair
)

$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$before = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

$params = @{
    ExecutionTimeLimit = (New-TimeSpan -Hours $ExecutionHours)
    MultipleInstances = "IgnoreNew"
    AllowStartIfOnBatteries = $true
    DontStopIfGoingOnBatteries = $true
    Hidden = $true
}

$cmd = Get-Command New-ScheduledTaskSettingsSet -ErrorAction Stop
if ($cmd.Parameters.ContainsKey("UseUnifiedSchedulingEngine")) {
    $params.UseUnifiedSchedulingEngine = $true
}

$settings = New-ScheduledTaskSettingsSet @params
Set-ScheduledTask -TaskName $TaskName -Settings $settings -ErrorAction Stop | Out-Null

$afterTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$after = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

$expected = New-TimeSpan -Hours $ExecutionHours
if ($afterTask.Settings.ExecutionTimeLimit -ne $expected) {
    throw "TASK_REPAIR_FAILED ExecutionTimeLimit=$($afterTask.Settings.ExecutionTimeLimit) expected=$expected"
}
if ($afterTask.Settings.MultipleInstances -ne "IgnoreNew") {
    throw "TASK_REPAIR_FAILED MultipleInstances=$($afterTask.Settings.MultipleInstances)"
}
if ($afterTask.Settings.DisallowStartIfOnBatteries) {
    throw "TASK_REPAIR_FAILED DisallowStartIfOnBatteries=true"
}
if ($afterTask.Settings.StopIfGoingOnBatteries) {
    throw "TASK_REPAIR_FAILED StopIfGoingOnBatteries=true"
}
if (-not $afterTask.Settings.Hidden) {
    throw "TASK_REPAIR_FAILED Hidden=false"
}

$result = [ordered]@{
    schema = "qrds.local_shadow.task_repair.v1"
    task = $TaskName
    repaired_at = (Get-Date).ToString("o")
    prior_last_run = $before.LastRunTime
    prior_last_result = $before.LastTaskResult
    execution_time_limit = $afterTask.Settings.ExecutionTimeLimit.ToString()
    multiple_instances = $afterTask.Settings.MultipleInstances.ToString()
    disallow_start_if_on_batteries = [bool]$afterTask.Settings.DisallowStartIfOnBatteries
    stop_if_going_on_batteries = [bool]$afterTask.Settings.StopIfGoingOnBatteries
    hidden = [bool]$afterTask.Settings.Hidden
    unified_scheduling_engine = [bool]$afterTask.Settings.UseUnifiedSchedulingEngine
    RESEARCH_ONLY = $true
    SHADOW_ONLY = $true
    ORDERS = 0
    REAL_CAPITAL = 0
}

if ($StartAfterRepair) {
    Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    Start-Sleep -Seconds 2
    $result.started_after_repair = $true
    $result.state_after_start = (Get-ScheduledTask -TaskName $TaskName).State.ToString()
} else {
    $result.started_after_repair = $false
}

$result | ConvertTo-Json -Depth 4
