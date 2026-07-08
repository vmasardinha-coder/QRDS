param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$serveScript = Join-Path $root "tools\serve_review_portal_research_only.ps1"
$portalIndex = Join-Path $root "artifacts\phase114_replay_evidence_export_review_portal_stub_research_only\index.html"

if (-not (Test-Path $serveScript)) {
  Write-Host "Serve script not found. Run Phase 122 first." -ForegroundColor Red
  exit 1
}

if (-not (Test-Path $portalIndex)) {
  Write-Host "Portal index not found. Run Phase 121 first." -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "QRDS one-command review portal runner"
Write-Host "Research-only mode"
Write-Host "Operational: BLOCKED_RESEARCH_ONLY"
Write-Host "Edge: False"
Write-Host "Decision layer allowed: False"
Write-Host "trading_signal_generated: False"
Write-Host "allocation_generated: False"
Write-Host "safe_apply_allowed: False"
Write-Host "canonical_data_writes: 0"
Write-Host ""
Write-Host "Open:"
Write-Host "  http://localhost:$Port/index.html"
Write-Host ""

& $serveScript -Port $Port
