$ErrorActionPreference = "Stop"
$projectRoot = "C:\QRDS\crypto_decision_lab"
$portalRoot = Join-Path $projectRoot "artifacts\phase324_scientific_next_family_decision_portal_research_only\portal"
if (-not (Test-Path (Join-Path $portalRoot "index.html") -PathType Leaf)) { throw "Phase 324 portal not found: $portalRoot" }
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start(); $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
Write-Host "QRDS Phase 324 local portal" -ForegroundColor Cyan
Write-Host "Root: $portalRoot"
Write-Host "URL: http://127.0.0.1:$port/"
Write-Host "Press Ctrl+C to stop."
Set-Location $portalRoot
& "C:\QRDS\crypto_decision_lab\.venv\Scripts\python.exe" -m http.server $port --bind 127.0.0.1
