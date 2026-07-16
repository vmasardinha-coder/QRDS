$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$projectRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$portalRoot = Join-Path $projectRoot "artifacts\phase334_synthetic_anti_leakage_review_portal_research_only\portal"

if (-not (Test-Path $pythonExe -PathType Leaf)) {
    throw "Project Python not found: $pythonExe"
}
if (-not (Test-Path (Join-Path $portalRoot "index.html") -PathType Leaf)) {
    throw "Phase 334 portal not found. Complete Batch 326-335 first."
}

$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    0
)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

Write-Host ""
Write-Host "=== QRDS PHASE 334 LOCAL PORTAL ===" -ForegroundColor Cyan
Write-Host "Research-only. No recommendation, order or capital."
Write-Host "Dynamic local port: $port"
Write-Host "URL: http://127.0.0.1:$port/"
Write-Host "Press CTRL+C to stop."
Write-Host ""

Set-Location $portalRoot
& $pythonExe -m http.server $port --bind 127.0.0.1
