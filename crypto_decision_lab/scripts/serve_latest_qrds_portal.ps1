$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$registryPath = Join-Path $projectRoot "artifacts\project_portal_registry\current_portal.json"

if (-not (Test-Path $pythonExe -PathType Leaf)) {
    throw "Project Python not found: $pythonExe"
}
if (-not (Test-Path $registryPath -PathType Leaf)) {
    throw "Current portal registry not found: $registryPath. Complete Phase 354 first."
}

$registry = Get-Content $registryPath -Raw | ConvertFrom-Json
$relativePath = [string]$registry.relative_path
if ([string]::IsNullOrWhiteSpace($relativePath)) {
    throw "Current portal registry does not contain relative_path."
}

$portalPath = Join-Path $projectRoot ($relativePath -replace "/", "\")
if (-not (Test-Path $portalPath -PathType Leaf)) {
    throw "Registered portal file not found: $portalPath"
}

function Get-FreeLocalPort {
    param([int]$StartPort = 51700, [int]$Attempts = 500)
    for ($port = $StartPort; $port -lt ($StartPort + $Attempts); $port++) {
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
            $listener.Start()
            $listener.Stop()
            return $port
        }
        catch {
            if ($null -ne $listener) {
                try { $listener.Stop() } catch {}
            }
        }
    }
    throw "No available local port found."
}

$port = Get-FreeLocalPort
$urlPath = ($relativePath -replace "\\", "/")
$url = "http://127.0.0.1:$port/$urlPath"

Write-Host "=== QRDS PORTAL READY ===" -ForegroundColor Green
Write-Host "Portal phase: $($registry.phase)"
Write-Host "Scientific status: $($registry.scientific_status)"
Write-Host "Operational: $($registry.operational_status)"
Write-Host "Action: $($registry.action_status)"
Write-Host 'Capital used: R$ 0'
Write-Host ""
Write-Host "LOCAL URL: $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "The browser will open automatically. Keep this PowerShell window open."
Write-Host "Press Ctrl+C to stop the local server."
Write-Host ""

$browserJob = $null
try {
    # Give the local server a brief moment to bind before the browser requests the page.
    $browserJob = Start-Job -ScriptBlock {
        param($TargetUrl)
        Start-Sleep -Milliseconds 1200
        Start-Process $TargetUrl
    } -ArgumentList $url
}
catch {
    Write-Host "Could not schedule automatic browser opening. Copy the LOCAL URL above." -ForegroundColor Yellow
}

try {
    & $pythonExe -m http.server $port --bind 127.0.0.1 --directory $projectRoot
}
finally {
    if ($null -ne $browserJob) {
        Receive-Job $browserJob -ErrorAction SilentlyContinue | Out-Null
        Remove-Job $browserJob -Force -ErrorAction SilentlyContinue
    }
}
