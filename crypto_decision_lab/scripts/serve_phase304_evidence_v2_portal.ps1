$ErrorActionPreference = "Stop"

$repoRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$portalDir = Join-Path $repoRoot "artifacts\phase304_nested_walk_forward_v2_research_only\portal"

if (-not (Test-Path $pythonExe -PathType Leaf)) {
    throw "Venv Python missing: $pythonExe"
}
if (-not (Test-Path (Join-Path $portalDir "index.html") -PathType Leaf)) {
    throw "Phase 304 portal missing. Complete Batch 301-305 first: $portalDir"
}

$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    0
)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

$url = "http://127.0.0.1:$port/"
Write-Host ""
Write-Host "=== QRDS PHASE 304 PORTAL - LOCAL SERVER ===" -ForegroundColor Cyan
Write-Host "Portal: $portalDir"
Write-Host "URL: $url" -ForegroundColor Green
Write-Host "Operational: BLOCKED_RESEARCH_ONLY"
Write-Host "Action: NO_ACTION_RESEARCH_ONLY"
Write-Host ""
Write-Host "No Codespaces: abra a URL acima no navegador." -ForegroundColor Yellow
Write-Host "Em Codespaces: abra a aba PORTS, localize a porta $port e use Open in Browser." -ForegroundColor Yellow
Write-Host "Pressione CTRL+C para encerrar o servidor."
Write-Host ""

& $pythonExe -m http.server $port --bind 127.0.0.1 --directory $portalDir
if ($LASTEXITCODE -ne 0) {
    throw "Local portal server failed with exit code $LASTEXITCODE."
}
