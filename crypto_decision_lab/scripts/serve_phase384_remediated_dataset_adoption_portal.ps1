$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0
$projectRoot = "C:\QRDS\crypto_decision_lab"
$portalRoot = Join-Path $projectRoot "artifacts\phase384_noncanonical_research_dataset_adoption_portal_research_only"
if (-not (Test-Path (Join-Path $portalRoot "index.html") -PathType Leaf)) {
    throw "Phase 384 portal not found: $portalRoot"
}
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe -PathType Leaf)) { throw "Project Python not found: $pythonExe" }
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0)
$listener.Start(); $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
Write-Host "Serving Phase 384 portal at http://127.0.0.1:$port/" -ForegroundColor Green
Write-Host "Codespaces: expose the printed port in the Ports tab if applicable."
Push-Location $portalRoot
try { & $pythonExe -m http.server $port --bind 127.0.0.1 } finally { Pop-Location }
