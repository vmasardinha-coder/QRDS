$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$gitRoot = $PSScriptRoot
$projectRoot = Join-Path $gitRoot "crypto_decision_lab"
$serveScript = Join-Path $projectRoot "scripts\serve_latest_qrds_portal.ps1"

if (-not (Test-Path $serveScript -PathType Leaf)) {
    throw "QRDS portal server script not found: $serveScript"
}

Write-Host ""
Write-Host "=== QRDS/QOS/GATE BTC - ABRIR PORTAL ATUAL ===" -ForegroundColor Cyan
Write-Host "Network required: NO"
Write-Host "Antivirus can remain enabled."
Write-Host "Operational: BLOCKED_RESEARCH_ONLY"
Write-Host "Action: NO_ACTION_RESEARCH_ONLY"
Write-Host 'Capital used: R$ 0'
Write-Host ""

& $serveScript
