$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$projectRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$portalRoot = Join-Path $projectRoot "artifacts\phase314_scientific_decision_portal_research_only\portal"
$indexPath = Join-Path $portalRoot "index.html"

if (-not (Test-Path $pythonExe -PathType Leaf)) {
    throw "Project Python not found: $pythonExe"
}
if (-not (Test-Path $indexPath -PathType Leaf)) {
    throw "Phase 314 portal not found: $indexPath"
}

$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    0
)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

$arguments = @(
    "-m", "http.server", "$port",
    "--bind", "127.0.0.1",
    "--directory", "`"$portalRoot`""
) -join " "

$process = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList $arguments `
    -WorkingDirectory $projectRoot `
    -PassThru

Start-Sleep -Milliseconds 700
if ($process.HasExited) {
    throw "Local portal server exited immediately with code $($process.ExitCode)."
}

$url = "http://127.0.0.1:$port/"
Write-Host ""
Write-Host "=== QRDS PHASE 314 LOCAL PORTAL SERVER ===" -ForegroundColor Cyan
Write-Host "URL: $url" -ForegroundColor Green
Write-Host "Server PID: $($process.Id)"
Write-Host "Portal root: $portalRoot"
Write-Host ""
Write-Host "Keep this PowerShell window available while using the portal."
Write-Host "To stop the server later:"
Write-Host "Stop-Process -Id $($process.Id)"
Write-Host ""
Write-Host "Codespaces only: expose port $port in the Ports tab and open the forwarded URL."
