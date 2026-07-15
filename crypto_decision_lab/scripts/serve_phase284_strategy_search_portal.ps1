$ErrorActionPreference="Stop"
$repoRoot="C:\QRDS\crypto_decision_lab"
$portalRoot=Join-Path $repoRoot "artifacts\phase276_285_strategy_search\strategy_search_portal"
$pythonExe=Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not(Test-Path $pythonExe -PathType Leaf)){throw "Venv Python missing: $pythonExe"}
if(-not(Test-Path (Join-Path $portalRoot "index.html") -PathType Leaf)){throw "Portal missing. Run Batch 276-285 first."}
$listener=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0);$listener.Start();$port=($listener.LocalEndpoint).Port;$listener.Stop()
Write-Host "";Write-Host "QRDS Phase 284 Strategy Search Portal";Write-Host "URL: http://127.0.0.1:$port/";Write-Host "Codespaces: open the Ports tab and set port $port visibility as needed.";Write-Host "Press Ctrl+C to stop.";Write-Host ""
Set-Location $portalRoot
& $pythonExe -m http.server $port --bind 127.0.0.1
