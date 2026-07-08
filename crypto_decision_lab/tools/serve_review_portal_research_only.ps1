param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$portalDir = Join-Path $root "artifacts\phase114_replay_evidence_export_review_portal_stub_research_only"
$indexFile = Join-Path $portalDir "index.html"
$reviewFile = Join-Path $portalDir "phase114_replay_evidence_export_review_portal_stub.html"

if (-not (Test-Path $indexFile)) {
  Write-Host "Portal index not found. Run Phase 121 first." -ForegroundColor Red
  exit 1
}

if (-not (Test-Path $reviewFile)) {
  Write-Host "Review portal artifact not found. Run Phase 114 first." -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "QRDS Review Portal Research-Only"
Write-Host "Operational: BLOCKED_RESEARCH_ONLY"
Write-Host "Edge: False"
Write-Host "Decision layer allowed: False"
Write-Host "trading_signal_generated: False"
Write-Host "allocation_generated: False"
Write-Host "safe_apply_allowed: False"
Write-Host "canonical_data_writes: 0"
Write-Host ""
Write-Host "Serving index:"
Write-Host "  http://localhost:$Port/index.html"
Write-Host ""
Write-Host "Review page:"
Write-Host "  http://localhost:$Port/phase114_replay_evidence_export_review_portal_stub.html"
Write-Host ""
Write-Host "Press CTRL+C to stop."
Write-Host ""

Set-Location $portalDir
python -m http.server $Port
