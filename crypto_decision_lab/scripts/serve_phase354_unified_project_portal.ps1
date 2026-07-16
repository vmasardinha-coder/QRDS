$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$latest = Join-Path $PSScriptRoot "serve_latest_qrds_portal.ps1"
if (-not (Test-Path $latest -PathType Leaf)) {
    throw "Latest portal server script not found: $latest"
}
& $latest
