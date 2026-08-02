[CmdletBinding()]
param(
    [string]$OutputDirectory = "",
    [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$StartedAt = Get-Date
$Stamp = $StartedAt.ToString("yyyyMMdd_HHmmss")
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $UserProfile = [Environment]::GetFolderPath("UserProfile")
    $Downloads = Join-Path $UserProfile "Downloads"
    if (Test-Path -LiteralPath $Downloads) {
        $OutputDirectory = $Downloads
    }
    else {
        $OutputDirectory = $BundleRoot
    }
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$TxtPath = Join-Path $OutputDirectory "GATE_BTC_WINDOWS_LOCAL_VERIFY_$Stamp.txt"
$JsonPath = Join-Path $OutputDirectory "GATE_BTC_WINDOWS_LOCAL_VERIFY_$Stamp.json"
$ZipPath = Join-Path $OutputDirectory "GATE_BTC_WINDOWS_LOCAL_VERIFY_EVIDENCE_$Stamp.zip"
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) "GATE_BTC_WINDOWS_LOCAL_VERIFY_${Stamp}_$PID"
$RuntimeRoot = Join-Path $TempRoot "runtime"
$LogRoot = Join-Path $TempRoot "logs"
$EvidenceRoot = Join-Path $TempRoot "evidence"

$Result = [ordered]@{
    schema = "gate-btc-windows-local-verifier-v1"
    status = "RUNNING"
    stage_reached = "INITIALIZE"
    started_at_local = $StartedAt.ToString("o")
    finished_at_local = $null
    bundle_root = $BundleRoot
    output_directory = $OutputDirectory
    report_txt = $TxtPath
    report_json = $JsonPath
    evidence_zip = $ZipPath
    temp_root = $TempRoot
    temp_removed = $false
    source_head_sha = $null
    source_head_ref = $null
    github_run_id = $null
    data_cutoff = $null
    bundle_integrity = "PENDING"
    python_version = $null
    dependency_install = "PENDING"
    v2a_status = "PENDING"
    v2a_output_members = $null
    v2a_max_abs_numeric_diff = $null
    v2a_max_rel_numeric_diff = $null
    delta_status = "PENDING"
    delta_output_members = $null
    delta_max_abs_numeric_diff = $null
    delta_max_rel_numeric_diff = $null
    network_actions = "NONE"
    project_files_modified = 0
    local_collection_read = $false
    local_collection_modified = $false
    research_only = $true
    orders_generated = 0
    real_capital_used = 0
    operational_status = "NOT_APPROVED"
    errors = @()
    next_action = "SEND_THIS_TXT_TO_CHAT"
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Add-VerifierError([string]$Message) {
    $script:Result.errors += $Message
}

function Invoke-CheckedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
    $SafeName = $Name -replace '[^A-Za-z0-9_.-]', '_'
    $StdoutPath = Join-Path $LogRoot "$SafeName.stdout.txt"
    $StderrPath = Join-Path $LogRoot "$SafeName.stderr.txt"

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments 1> $StdoutPath 2> $StderrPath
        $ExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($ExitCode -ne 0) {
        $StdoutTail = if (Test-Path -LiteralPath $StdoutPath) {
            (Get-Content -LiteralPath $StdoutPath -Tail 40 -ErrorAction SilentlyContinue) -join "`n"
        }
        else { "" }
        $StderrTail = if (Test-Path -LiteralPath $StderrPath) {
            (Get-Content -LiteralPath $StderrPath -Tail 80 -ErrorAction SilentlyContinue) -join "`n"
        }
        else { "" }
        throw "$Name failed with exit code $ExitCode.`nSTDOUT_TAIL:`n$StdoutTail`nSTDERR_TAIL:`n$StderrTail"
    }
}

function Get-LatestJson([string]$Directory, [string]$Pattern) {
    $Item = Get-ChildItem -LiteralPath $Directory -Filter $Pattern -File -ErrorAction Stop |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if ($null -eq $Item) {
        throw "No JSON matching $Pattern under $Directory"
    }
    return Get-Content -LiteralPath $Item.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
}

try {
    $Result.stage_reached = "SAFETY_LOCKS"
    if ($env:GATE_BTC_RESEARCH_ONLY -and $env:GATE_BTC_RESEARCH_ONLY.ToLowerInvariant() -ne "true") {
        throw "GATE_BTC_RESEARCH_ONLY must remain true"
    }
    foreach ($Forbidden in @("EXCHANGE_API_SECRET", "EXCHANGE_PRIVATE_KEY", "TRADING_API_KEY")) {
        $Value = [Environment]::GetEnvironmentVariable($Forbidden)
        if (-not [string]::IsNullOrWhiteSpace($Value)) {
            throw "Forbidden operational credential is present in environment: $Forbidden"
        }
    }
    $env:GATE_BTC_RESEARCH_ONLY = "true"
    $env:PYTHONDONTWRITEBYTECODE = "1"

    $Result.stage_reached = "VERIFY_BUNDLE_MANIFEST"
    $ManifestPath = Join-Path $BundleRoot "BUNDLE_MANIFEST.json"
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        throw "Missing bundle manifest: $ManifestPath"
    }
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Manifest.schema -ne "gate-btc-windows-local-verifier-bundle-v1") {
        throw "Unexpected bundle manifest schema: $($Manifest.schema)"
    }
    if ($Manifest.research_only -ne $true -or $Manifest.orders_generated -ne 0 -or $Manifest.real_capital_used -ne 0) {
        throw "Bundle manifest violates research-only zero-order zero-capital locks"
    }
    $Result.source_head_sha = $Manifest.source_head_sha
    $Result.source_head_ref = $Manifest.source_head_ref
    $Result.github_run_id = $Manifest.github_run_id
    $Result.data_cutoff = $Manifest.data_cutoff

    $ManifestFiles = @($Manifest.files_sha256.PSObject.Properties)
    if ($ManifestFiles.Count -lt 1) {
        throw "Bundle manifest contains no file hashes"
    }
    foreach ($Property in $ManifestFiles) {
        $Relative = $Property.Name.Replace('/', [IO.Path]::DirectorySeparatorChar)
        $Expected = [string]$Property.Value
        $ActualPath = Join-Path $BundleRoot $Relative
        if (-not (Test-Path -LiteralPath $ActualPath -PathType Leaf)) {
            throw "Bundle file is missing: $($Property.Name)"
        }
        $Actual = Get-Sha256 $ActualPath
        if ($Actual -ne $Expected.ToLowerInvariant()) {
            throw "Bundle hash mismatch for $($Property.Name): expected=$Expected actual=$Actual"
        }
    }
    $Result.bundle_integrity = "PASS"

    $Result.stage_reached = "LOCATE_PYTHON_312"
    $PythonExe = $null
    $PythonPrefix = @()
    $PythonCandidates = @()
    $PyLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($null -ne $PyLauncher) {
        $PythonCandidates += [pscustomobject]@{ Exe = $PyLauncher.Source; Prefix = @("-3.12") }
    }
    $PythonCommand = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) {
        $PythonCandidates += [pscustomobject]@{ Exe = $PythonCommand.Source; Prefix = @() }
    }
    foreach ($Candidate in $PythonCandidates) {
        $CandidateOutput = (& $Candidate.Exe @($Candidate.Prefix) -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $CandidateOutput.StartsWith("3.12.")) {
            $PythonExe = $Candidate.Exe
            $PythonPrefix = @($Candidate.Prefix)
            $Result.python_version = $CandidateOutput
            break
        }
    }
    if ([string]::IsNullOrWhiteSpace($PythonExe)) {
        throw "Python 3.12 was not found. The existing GATE BTC environment normally provides it."
    }

    $Result.stage_reached = "PREPARE_ISOLATED_RUNTIME"
    New-Item -ItemType Directory -Force -Path $TempRoot, $RuntimeRoot, $LogRoot, $EvidenceRoot | Out-Null
    $BundledRuntime = Join-Path $BundleRoot "payload\runtime"
    if (-not (Test-Path -LiteralPath $BundledRuntime -PathType Container)) {
        throw "Missing bundled runtime: $BundledRuntime"
    }
    Copy-Item -Path (Join-Path $BundledRuntime "*") -Destination $RuntimeRoot -Recurse -Force

    $VenvRoot = Join-Path $TempRoot ".venv"
    Invoke-CheckedProcess -Name "create_venv" -FilePath $PythonExe -Arguments @($PythonPrefix + @("-m", "venv", $VenvRoot)) -WorkingDirectory $TempRoot
    $VenvPython = Join-Path $VenvRoot "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        throw "Isolated Python was not created: $VenvPython"
    }

    $Result.stage_reached = "INSTALL_OFFLINE_DEPENDENCIES"
    $Wheelhouse = Join-Path $BundleRoot "payload\wheelhouse"
    if (-not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
        throw "Missing offline wheelhouse: $Wheelhouse"
    }
    $V2ARequirements = Join-Path $RuntimeRoot "migration\canonical\v2a\requirements.txt"
    $DeltaRequirements = Join-Path $RuntimeRoot "migration\canonical\delta\requirements.txt"
    Invoke-CheckedProcess -Name "install_offline_dependencies" -FilePath $VenvPython -Arguments @(
        "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--find-links", $Wheelhouse,
        "-r", $V2ARequirements, "-r", $DeltaRequirements
    ) -WorkingDirectory $RuntimeRoot
    $Result.dependency_install = "PASS_OFFLINE_NO_INDEX"

    $ReferenceRoot = Join-Path $BundleRoot "payload\reference"
    $ReferenceV2A = Join-Path $ReferenceRoot "qos_v2a_outputs.zip"
    $ReferenceDelta = Join-Path $ReferenceRoot "delta_walk_forward_outputs.zip"
    $ReferenceDeltaInput = Join-Path $ReferenceRoot "delta_public_input_snapshot.zip"
    foreach ($Required in @($ReferenceV2A, $ReferenceDelta, $ReferenceDeltaInput)) {
        if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
            throw "Missing frozen reference package: $Required"
        }
    }

    $V2AOutput = Join-Path $EvidenceRoot "windows_v2a_outputs.zip"
    $V2AEvidence = Join-Path $EvidenceRoot "v2a_replay_evidence"
    $V2AParity = Join-Path $EvidenceRoot "v2a_windows_parity"
    $Result.stage_reached = "REPLAY_V2A_SAME_INPUT"
    Invoke-CheckedProcess -Name "v2a_frozen_replay" -FilePath $VenvPython -Arguments @(
        "tools/v2a_frozen_replay.py", $ReferenceV2A,
        "--data-cutoff", [string]$Manifest.data_cutoff,
        "--output-zip", $V2AOutput,
        "--evidence-dir", $V2AEvidence
    ) -WorkingDirectory $RuntimeRoot
    Invoke-CheckedProcess -Name "v2a_cross_platform_compare" -FilePath $VenvPython -Arguments @(
        "tools/compare_cross_platform_outputs.py", "v2a", $ReferenceV2A, $V2AOutput,
        "--output-dir", $V2AParity
    ) -WorkingDirectory $RuntimeRoot
    $V2AResult = Get-LatestJson $V2AParity "V2A_CROSS_PLATFORM_PARITY_*.json"
    if ($V2AResult.status -ne "PASS" -or $V2AResult.equivalence_claim -ne $true) {
        throw "V2A semantic parity did not pass"
    }
    $Result.v2a_status = "PASS"
    $Result.v2a_output_members = "$($V2AResult.output_members_matched)/$($V2AResult.output_members_checked)"
    $Result.v2a_max_abs_numeric_diff = $V2AResult.observed_max_abs_numeric_diff
    $Result.v2a_max_rel_numeric_diff = $V2AResult.observed_max_rel_numeric_diff

    $DeltaOutput = Join-Path $EvidenceRoot "windows_delta_outputs.zip"
    $DeltaInputReplay = Join-Path $EvidenceRoot "windows_delta_input_snapshot.zip"
    $DeltaEvidence = Join-Path $EvidenceRoot "delta_replay_evidence"
    $DeltaParity = Join-Path $EvidenceRoot "delta_windows_parity"
    $Result.stage_reached = "REPLAY_DELTA_SAME_INPUT"
    Invoke-CheckedProcess -Name "delta_frozen_replay" -FilePath $VenvPython -Arguments @(
        "tools/delta_frozen_replay.py", $ReferenceDeltaInput,
        "--data-cutoff", [string]$Manifest.data_cutoff,
        "--output-zip", $DeltaOutput,
        "--input-snapshot-zip", $DeltaInputReplay,
        "--evidence-dir", $DeltaEvidence
    ) -WorkingDirectory $RuntimeRoot
    Invoke-CheckedProcess -Name "delta_cross_platform_compare" -FilePath $VenvPython -Arguments @(
        "tools/compare_cross_platform_outputs.py", "delta", $ReferenceDelta, $DeltaOutput,
        "--reference-input-snapshot", $ReferenceDeltaInput,
        "--replay-input-snapshot", $DeltaInputReplay,
        "--output-dir", $DeltaParity
    ) -WorkingDirectory $RuntimeRoot
    $DeltaResult = Get-LatestJson $DeltaParity "DELTA_CROSS_PLATFORM_PARITY_*.json"
    if ($DeltaResult.status -ne "PASS" -or $DeltaResult.equivalence_claim -ne $true) {
        throw "Delta semantic parity did not pass"
    }
    $Result.delta_status = "PASS"
    $Result.delta_output_members = "$($DeltaResult.output_members_matched)/$($DeltaResult.output_members_checked)"
    $Result.delta_max_abs_numeric_diff = $DeltaResult.observed_max_abs_numeric_diff
    $Result.delta_max_rel_numeric_diff = $DeltaResult.observed_max_rel_numeric_diff

    $Result.status = "PASS"
    $Result.stage_reached = "WINDOWS_LOCAL_SAME_INPUT_PARITY_COMPLETE"
}
catch {
    $Result.status = "ERROR"
    Add-VerifierError ("{0}: {1}`n{2}" -f $_.Exception.GetType().FullName, $_.Exception.Message, $_.ScriptStackTrace)
    if ($Result.v2a_status -eq "PENDING") { $Result.v2a_status = "NOT_COMPLETED" }
    if ($Result.delta_status -eq "PENDING") { $Result.delta_status = "NOT_COMPLETED" }
}
finally {
    $Result.finished_at_local = (Get-Date).ToString("o")

    $ErrorLines = if ($Result.errors.Count -gt 0) { $Result.errors } else { @("NONE") }
    $Lines = @(
        "GATE BTC - WINDOWS LOCAL SAME-INPUT VERIFIER",
        "STATUS=$($Result.status)",
        "STAGE_REACHED=$($Result.stage_reached)",
        "STARTED_AT_LOCAL=$($Result.started_at_local)",
        "FINISHED_AT_LOCAL=$($Result.finished_at_local)",
        "SOURCE_HEAD_SHA=$($Result.source_head_sha)",
        "SOURCE_HEAD_REF=$($Result.source_head_ref)",
        "GITHUB_RUN_ID=$($Result.github_run_id)",
        "DATA_CUTOFF=$($Result.data_cutoff)",
        "BUNDLE_INTEGRITY=$($Result.bundle_integrity)",
        "PYTHON_VERSION=$($Result.python_version)",
        "DEPENDENCY_INSTALL=$($Result.dependency_install)",
        "V2A_STATUS=$($Result.v2a_status)",
        "V2A_OUTPUT_MEMBERS=$($Result.v2a_output_members)",
        "V2A_MAX_ABS_NUMERIC_DIFF=$($Result.v2a_max_abs_numeric_diff)",
        "V2A_MAX_REL_NUMERIC_DIFF=$($Result.v2a_max_rel_numeric_diff)",
        "DELTA_STATUS=$($Result.delta_status)",
        "DELTA_OUTPUT_MEMBERS=$($Result.delta_output_members)",
        "DELTA_MAX_ABS_NUMERIC_DIFF=$($Result.delta_max_abs_numeric_diff)",
        "DELTA_MAX_REL_NUMERIC_DIFF=$($Result.delta_max_rel_numeric_diff)",
        "NETWORK_ACTIONS=NONE",
        "PROJECT_FILES_MODIFIED=0",
        "LOCAL_COLLECTION_READ=False",
        "LOCAL_COLLECTION_MODIFIED=False",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "REPORT_JSON=$JsonPath",
        "EVIDENCE_ZIP=$ZipPath",
        "NEXT_ACTION=$($Result.next_action)",
        "",
        "ERRORS:",
        $ErrorLines
    )

    $Result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
    $Lines | Set-Content -LiteralPath $TxtPath -Encoding UTF8

    $ZipStage = Join-Path $TempRoot "zip_stage"
    try {
        New-Item -ItemType Directory -Force -Path $ZipStage | Out-Null
        Copy-Item -LiteralPath $TxtPath, $JsonPath -Destination $ZipStage -Force
        if (Test-Path -LiteralPath $LogRoot) {
            Copy-Item -LiteralPath $LogRoot -Destination (Join-Path $ZipStage "logs") -Recurse -Force
        }
        if (Test-Path -LiteralPath $EvidenceRoot) {
            Copy-Item -LiteralPath $EvidenceRoot -Destination (Join-Path $ZipStage "evidence") -Recurse -Force
        }
        if (Test-Path -LiteralPath $ZipPath) {
            Remove-Item -LiteralPath $ZipPath -Force
        }
        Compress-Archive -Path (Join-Path $ZipStage "*") -DestinationPath $ZipPath -CompressionLevel Optimal -Force
    }
    catch {
        Add-VerifierError ("Evidence ZIP generation failed: {0}" -f $_.Exception.Message)
        $Result.status = "ERROR"
        $Result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
        Add-Content -LiteralPath $TxtPath -Value ("EVIDENCE_ZIP_ERROR={0}" -f $_.Exception.Message) -Encoding UTF8
    }

    if (-not $KeepTemp -and (Test-Path -LiteralPath $TempRoot)) {
        try {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
            $Result.temp_removed = $true
        }
        catch {
            Add-Content -LiteralPath $TxtPath -Value ("TEMP_CLEANUP_WARNING={0}" -f $_.Exception.Message) -Encoding UTF8
        }
    }

    $Result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
}

Write-Host ""
Write-Host "GATE BTC local verification status: $($Result.status)"
Write-Host "Send this TXT to the chat: $TxtPath"
Write-Host "Evidence ZIP: $ZipPath"

if ($Result.status -eq "PASS") {
    exit 0
}
exit 1
