[CmdletBinding()]
param(
    [string]$OutputDirectory = "",
    [string[]]$Roots = @(),
    [int]$MaxZipCount = 2000,
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$StartedAt = Get-Date
$Stamp = $StartedAt.ToString("yyyyMMdd_HHmmss")
$UserProfile = [Environment]::GetFolderPath("UserProfile")

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $Downloads = Join-Path $UserProfile "Downloads"
    $OutputDirectory = if (Test-Path -LiteralPath $Downloads) { $Downloads } else { $UserProfile }
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$TxtPath = Join-Path $OutputDirectory "GATE_BTC_GATEWAY_SOURCE_LOCATOR_$Stamp.txt"
$JsonPath = Join-Path $OutputDirectory "GATE_BTC_GATEWAY_SOURCE_LOCATOR_$Stamp.json"
$Stopwatch = [Diagnostics.Stopwatch]::StartNew()

$ExactNames = @(
    "qos_v2a1_gateway_scanner_v0_9.zip",
    "qos_master_pipeline_v0_2.zip",
    "qos_master_outputs.zip",
    "qos_v2a1_gateway_outputs.zip",
    "qos_v2a1_gateway_scanner_v0_8.zip",
    "qos_v2a1_gateway_scanner_v0_7.zip",
    "qos_master_pipeline_v0_1.zip"
)
$ExactLookup = @{}
foreach ($Name in $ExactNames) {
    $ExactLookup[$Name.ToLowerInvariant()] = $true
}

$NamePattern = '(?i)(qos.*gateway|gateway.*qos|v2a1.*gateway|qos[_-]?master[_-]?pipeline|qos[_-]?master[_-]?outputs)'
$EntryPattern = '(?i)(gateway|scanner|coingecko_top500|delta_ls_70_30|delta_ls_50_50|bybit_loaded|qos_v2a1)'
$SourceExtensions = @(".zip", ".py", ".ps1", ".ipynb", ".json", ".md", ".txt")

$Result = [ordered]@{
    schema = "gate-btc-gateway-source-locator-v1"
    status = "RUNNING"
    source_discovery_status = "PENDING"
    started_at_local = $StartedAt.ToString("o")
    finished_at_local = $null
    output_directory = $OutputDirectory
    report_txt = $TxtPath
    report_json = $JsonPath
    roots = @()
    files_examined = 0
    zip_files_examined = 0
    exact_candidate_count = 0
    named_candidate_count = 0
    archive_candidate_count = 0
    candidates = @()
    scan_warnings = @()
    network_actions = "NONE"
    searched_files_modified = 0
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

function Add-UniqueRoot {
    param(
        [Parameter(Mandatory = $true)][System.Collections.Generic.List[string]]$List,
        [Parameter(Mandatory = $true)][hashtable]$Seen,
        [string]$Path
    )
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    try {
        $Resolved = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    }
    catch {
        return
    }
    if (-not (Test-Path -LiteralPath $Resolved -PathType Container)) { return }
    $Key = $Resolved.ToLowerInvariant()
    if (-not $Seen.ContainsKey($Key)) {
        $Seen[$Key] = $true
        [void]$List.Add($Resolved)
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Add-Candidate {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Map,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Kind,
        [string[]]$MatchedEntries = @()
    )
    $Key = $Path.ToLowerInvariant()
    if (-not $Map.ContainsKey($Key)) {
        $Item = Get-Item -LiteralPath $Path -ErrorAction Stop
        $Map[$Key] = [ordered]@{
            path = $Item.FullName
            kind = $Kind
            name = $Item.Name
            size_bytes = [int64]$Item.Length
            last_write_time_local = $Item.LastWriteTime.ToString("o")
            sha256 = Get-Sha256 -Path $Item.FullName
            matched_entries = @($MatchedEntries | Select-Object -First 50)
        }
        return
    }

    if ($MatchedEntries.Count -gt 0) {
        $Existing = @($Map[$Key].matched_entries)
        $Map[$Key].matched_entries = @($Existing + $MatchedEntries | Sort-Object -Unique | Select-Object -First 50)
    }
}

function Write-Reports {
    $Result.finished_at_local = (Get-Date).ToString("o")
    $Json = $Result | ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText($JsonPath, $Json, [Text.UTF8Encoding]::new($false))

    $Lines = New-Object System.Collections.Generic.List[string]
    foreach ($Line in @(
        "GATE BTC - GATEWAY SOURCE LOCATOR",
        "STATUS=$($Result.status)",
        "SOURCE_DISCOVERY_STATUS=$($Result.source_discovery_status)",
        "STARTED_AT_LOCAL=$($Result.started_at_local)",
        "FINISHED_AT_LOCAL=$($Result.finished_at_local)",
        "FILES_EXAMINED=$($Result.files_examined)",
        "ZIP_FILES_EXAMINED=$($Result.zip_files_examined)",
        "EXACT_CANDIDATE_COUNT=$($Result.exact_candidate_count)",
        "NAMED_CANDIDATE_COUNT=$($Result.named_candidate_count)",
        "ARCHIVE_CANDIDATE_COUNT=$($Result.archive_candidate_count)",
        "NETWORK_ACTIONS=NONE",
        "SEARCHED_FILES_MODIFIED=0",
        "PROJECT_FILES_MODIFIED=0",
        "LOCAL_COLLECTION_READ=False",
        "LOCAL_COLLECTION_MODIFIED=False",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "REPORT_JSON=$JsonPath",
        "NEXT_ACTION=SEND_THIS_TXT_TO_CHAT",
        "",
        "ROOTS:"
    )) { [void]$Lines.Add($Line) }

    foreach ($Root in @($Result.roots)) { [void]$Lines.Add($Root) }
    [void]$Lines.Add("")
    [void]$Lines.Add("CANDIDATES:")
    if (@($Result.candidates).Count -eq 0) {
        [void]$Lines.Add("NONE")
    }
    else {
        foreach ($Candidate in @($Result.candidates)) {
            [void]$Lines.Add("KIND=$($Candidate.kind)")
            [void]$Lines.Add("PATH=$($Candidate.path)")
            [void]$Lines.Add("SIZE_BYTES=$($Candidate.size_bytes)")
            [void]$Lines.Add("LAST_WRITE_TIME_LOCAL=$($Candidate.last_write_time_local)")
            [void]$Lines.Add("SHA256=$($Candidate.sha256)")
            foreach ($Entry in @($Candidate.matched_entries)) {
                [void]$Lines.Add("MATCHED_ENTRY=$Entry")
            }
            [void]$Lines.Add("")
        }
    }

    [void]$Lines.Add("SCAN_WARNINGS:")
    if (@($Result.scan_warnings).Count -eq 0) { [void]$Lines.Add("NONE") }
    else { foreach ($Warning in @($Result.scan_warnings)) { [void]$Lines.Add($Warning) } }
    [void]$Lines.Add("")
    [void]$Lines.Add("ERRORS:")
    if (@($Result.errors).Count -eq 0) { [void]$Lines.Add("NONE") }
    else { foreach ($ErrorMessage in @($Result.errors)) { [void]$Lines.Add($ErrorMessage) } }

    [IO.File]::WriteAllLines($TxtPath, $Lines, [Text.UTF8Encoding]::new($false))
}

$ExitCode = 1
try {
    if ($env:GATE_BTC_RESEARCH_ONLY -and $env:GATE_BTC_RESEARCH_ONLY.ToLowerInvariant() -ne "true") {
        throw "GATE_BTC_RESEARCH_ONLY must remain true"
    }
    if ($MaxZipCount -lt 1 -or $MaxZipCount -gt 10000) {
        throw "MaxZipCount must be between 1 and 10000"
    }
    if ($TimeoutSeconds -lt 30 -or $TimeoutSeconds -gt 3600) {
        throw "TimeoutSeconds must be between 30 and 3600"
    }

    $RootList = [System.Collections.Generic.List[string]]::new()
    $RootSeen = @{}
    if (@($Roots).Count -gt 0) {
        foreach ($Root in $Roots) { Add-UniqueRoot -List $RootList -Seen $RootSeen -Path $Root }
    }
    else {
        foreach ($DefaultRoot in @(
            (Join-Path $UserProfile "Downloads"),
            (Join-Path $UserProfile "Desktop"),
            (Join-Path $UserProfile "Documents"),
            $env:OneDrive,
            $env:OneDriveConsumer,
            $env:OneDriveCommercial,
            (Join-Path $UserProfile "OneDrive"),
            $env:GOOGLE_DRIVE,
            $env:GOOGLEDRIVE,
            (Join-Path $UserProfile "Google Drive"),
            (Join-Path $UserProfile "My Drive"),
            (Join-Path $UserProfile "Meu Drive")
        )) {
            Add-UniqueRoot -List $RootList -Seen $RootSeen -Path $DefaultRoot
        }
    }

    if ($RootList.Count -eq 0) {
        throw "No valid search roots were found"
    }
    $Result.roots = @($RootList)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Candidates = @{}
    $InspectedZipPaths = @{}

    foreach ($Root in $RootList) {
        if ($Stopwatch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
            $Result.scan_warnings += "TIMEOUT_REACHED before root completed: $Root"
            break
        }

        $Files = Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue
        foreach ($File in $Files) {
            if ($Stopwatch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
                $Result.scan_warnings += "TIMEOUT_REACHED during scan of root: $Root"
                break
            }

            $Result.files_examined++
            $Extension = $File.Extension.ToLowerInvariant()
            $LowerName = $File.Name.ToLowerInvariant()
            $IsExact = $ExactLookup.ContainsKey($LowerName)
            $IsNamedCandidate = ($SourceExtensions -contains $Extension) -and ($File.Name -match $NamePattern)

            if ($IsExact) {
                Add-Candidate -Map $Candidates -Path $File.FullName -Kind "EXACT_FILENAME"
            }
            elseif ($IsNamedCandidate) {
                Add-Candidate -Map $Candidates -Path $File.FullName -Kind "NAME_MATCH"
            }

            if ($Extension -ne ".zip") { continue }
            if ($Result.zip_files_examined -ge $MaxZipCount) {
                if (-not ($Result.scan_warnings -contains "MAX_ZIP_COUNT_REACHED=$MaxZipCount")) {
                    $Result.scan_warnings += "MAX_ZIP_COUNT_REACHED=$MaxZipCount"
                }
                continue
            }
            if ($File.Length -gt 1073741824) {
                $Result.scan_warnings += "ZIP_SKIPPED_OVER_1GB=$($File.FullName)"
                continue
            }

            $ZipKey = $File.FullName.ToLowerInvariant()
            if ($InspectedZipPaths.ContainsKey($ZipKey)) { continue }
            $InspectedZipPaths[$ZipKey] = $true
            $Result.zip_files_examined++

            $Archive = $null
            try {
                $Archive = [IO.Compression.ZipFile]::OpenRead($File.FullName)
                $MatchedEntries = @(
                    $Archive.Entries |
                        Where-Object { $_.FullName -match $EntryPattern } |
                        Select-Object -ExpandProperty FullName -First 50
                )
                if ($MatchedEntries.Count -gt 0) {
                    Add-Candidate -Map $Candidates -Path $File.FullName -Kind "ZIP_CONTENT_MATCH" -MatchedEntries $MatchedEntries
                }
            }
            catch {
                $Result.scan_warnings += "ZIP_INSPECTION_FAILED=$($File.FullName) :: $($_.Exception.Message)"
            }
            finally {
                if ($null -ne $Archive) { $Archive.Dispose() }
            }
        }
    }

    $CandidateValues = @($Candidates.Values | Sort-Object @{Expression = {
        switch ($_.kind) {
            "EXACT_FILENAME" { 0 }
            "NAME_MATCH" { 1 }
            default { 2 }
        }
    }}, path)
    $Result.candidates = $CandidateValues
    $Result.exact_candidate_count = @($CandidateValues | Where-Object { $_.kind -eq "EXACT_FILENAME" }).Count
    $Result.named_candidate_count = @($CandidateValues | Where-Object { $_.kind -eq "NAME_MATCH" }).Count
    $Result.archive_candidate_count = @($CandidateValues | Where-Object { $_.matched_entries.Count -gt 0 }).Count
    $Result.source_discovery_status = if ($CandidateValues.Count -gt 0) { "FOUND_CANDIDATES" } else { "NOT_FOUND" }
    $Result.status = "PASS"
    $ExitCode = 0
}
catch {
    $Result.status = "ERROR"
    $Result.source_discovery_status = "INCOMPLETE"
    $Result.errors += ($_ | Out-String).Trim()
    $ExitCode = 1
}
finally {
    $Stopwatch.Stop()
    Write-Reports
    Write-Host "GATE BTC Gateway source locator finished: $($Result.status)"
    Write-Host "TXT: $TxtPath"
    Write-Host "JSON: $JsonPath"
}

exit $ExitCode
