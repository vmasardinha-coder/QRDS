param(
    [Parameter(Mandatory=$true)][string]$InstallerPath,
    [Parameter(Mandatory=$true)][string]$ReportPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$projectRoot = "C:\QRDS\crypto_decision_lab"
$paths = @(
    [string]$InstallerPath,
    [string](Join-Path $projectRoot "scripts\qrds_release_gate_376_385.ps1"),
    [string](Join-Path $projectRoot "scripts\serve_phase384_remediated_dataset_adoption_portal.ps1")
)

# Native arrays are intentional. Windows PowerShell 5.1 can throw
# "Argument types do not match" when a generic List[object] is coerced by @(...).
$errors = @()
$parsedFiles = @()

foreach ($path in $paths) {
    $record = [ordered]@{
        path = [string]$path
        exists = $false
        parsed = $false
        token_count = 0
        parse_error_count = 0
        exception_type = $null
        exception_message = $null
    }

    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $errors += [pscustomobject][ordered]@{
            path = [string]$path
            category = "MISSING_FILE"
            message = "MISSING_FILE"
            line = $null
            column = $null
            extent = $null
            exception_type = $null
        }
        $parsedFiles += [pscustomobject]$record
        continue
    }

    $record.exists = $true

    try {
        # The exact array types are required by Parser.ParseFile overload binding
        # in Windows PowerShell 5.1. Untyped $null refs are forbidden.
        [System.Management.Automation.Language.Token[]]$tokens = @()
        [System.Management.Automation.Language.ParseError[]]$parseErrors = @()

        $null = [System.Management.Automation.Language.Parser]::ParseFile(
            [string]$path,
            [ref]$tokens,
            [ref]$parseErrors
        )

        $record.parsed = $true
        $record.token_count = [int]$tokens.Count
        $record.parse_error_count = [int]$parseErrors.Count

        foreach ($parseError in $parseErrors) {
            $errors += [pscustomobject][ordered]@{
                path = [string]$path
                category = "POWERSHELL_PARSE_ERROR"
                message = [string]$parseError.Message
                line = [int]$parseError.Extent.StartLineNumber
                column = [int]$parseError.Extent.StartColumnNumber
                extent = [string]$parseError.Extent.Text
                exception_type = $null
            }
        }
    }
    catch {
        $record.exception_type = [string]$_.Exception.GetType().FullName
        $record.exception_message = [string]$_.Exception.Message
        $errors += [pscustomobject][ordered]@{
            path = [string]$path
            category = "PARSER_INVOCATION_EXCEPTION"
            message = [string]$_.Exception.Message
            line = if ($_.InvocationInfo) { [int]$_.InvocationInfo.ScriptLineNumber } else { $null }
            column = if ($_.InvocationInfo) { [int]$_.InvocationInfo.OffsetInLine } else { $null }
            extent = if ($_.InvocationInfo) { [string]$_.InvocationInfo.Line } else { $null }
            exception_type = [string]$_.Exception.GetType().FullName
        }
    }

    $parsedFiles += [pscustomobject]$record
}

$report = [ordered]@{
    schema = "qrds.phase383.powershell_parser_report.v2"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    powershell_edition = [string]$PSVersionTable.PSEdition
    powershell_version = [string]$PSVersionTable.PSVersion
    parsed_file_count = [int]$paths.Count
    successfully_parsed_file_count = [int](@($parsedFiles | Where-Object { $_.parsed -eq $true }).Count)
    error_count = [int]$errors.Count
    parsed_files = [object[]]$parsedFiles
    errors = [object[]]$errors
    passed = ($errors.Count -eq 0 -and @($parsedFiles | Where-Object { $_.parsed -eq $true }).Count -eq $paths.Count)
}

$parent = Split-Path -Parent $ReportPath
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ReportPath -Encoding UTF8

if (-not $report.passed) {
    Write-Host ($report | ConvertTo-Json -Depth 12) -ForegroundColor Red
    throw "PowerShell parser release gate failed. See $ReportPath"
}

Write-Host "QRDS_RELEASE_GATE_POWERSHELL_PARSER: PASS" -ForegroundColor Green
Write-Host "PowerShell: $($report.powershell_edition) $($report.powershell_version)"
Write-Host "Parsed files: $($report.successfully_parsed_file_count)/$($report.parsed_file_count)"
