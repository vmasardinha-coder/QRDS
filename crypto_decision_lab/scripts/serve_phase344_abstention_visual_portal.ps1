$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$projectRoot = "C:\QRDS\crypto_decision_lab"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$portalRoot = Join-Path $projectRoot "artifacts\phase344_abstention_visual_interpretation_portal_research_only\portal"

if (-not (Test-Path $python -PathType Leaf)) {
    throw "Virtualenv Python not found: $python"
}
if (-not (Test-Path (Join-Path $portalRoot "index.html") -PathType Leaf)) {
    throw "Phase 344 portal not found. Run Batch 336-345 first."
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

Write-Host ""
Write-Host "=== QRDS PHASE 344 LOCAL PORTAL ===" -ForegroundColor Cyan
Write-Host "Portal root: $portalRoot"
Write-Host "Local URL: http://127.0.0.1:$port/"
Write-Host "Research only: BLOCKED_RESEARCH_ONLY | NO_ACTION_RESEARCH_ONLY | capital R$ 0"
Write-Host ""
Write-Host "Codespaces/remote environment: expose port $port in the Ports panel and open the forwarded URL."
Write-Host "Press Ctrl+C to stop the server."
Write-Host ""

Set-Location $portalRoot
& $python -m http.server $port --bind 127.0.0.1
