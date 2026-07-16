$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$projectRoot = "C:\QRDS\crypto_decision_lab"
$portalRoot = Join-Path $projectRoot "artifacts\phase374_data_quality_remediation_result_portal_research_only\portal"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $portalRoot -PathType Container)) {
    throw "Phase 374 portal was not found: $portalRoot"
}
if (-not (Test-Path (Join-Path $portalRoot "index.html") -PathType Leaf)) {
    throw "Phase 374 portal index was not found."
}
if (-not (Test-Path $python -PathType Leaf)) {
    throw "Project Python was not found: $python"
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

$url = "http://127.0.0.1:$port/"
Write-Host ""
Write-Host "=== QRDS PHASE 374 PORTAL SERVER ===" -ForegroundColor Cyan
Write-Host "Antivirus may remain enabled. This is a local server only."
Write-Host "LOCAL URL: $url" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server."
Write-Host ""

Start-Process $url
Set-Location $portalRoot
& $python -m http.server $port --bind 127.0.0.1
