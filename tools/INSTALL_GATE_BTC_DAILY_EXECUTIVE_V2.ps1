param(
  [string]$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  [string]$InstallDir = "C:\GATE_BTC_PROJECT\RUNTIME\DAILY_EXECUTIVE_V2",
  [string]$TaskName = "GATE BTC Daily Executive Reconciler",
  [string]$DailyTime = "22:35"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here "GATE_BTC_DAILY_EXECUTIVE_RECONCILER_V2.py"
if (-not (Test-Path $src)) { throw "Missing $src" }
if (-not (Test-Path $Python)) { throw "Python not found: $Python" }

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item $src (Join-Path $InstallDir "GATE_BTC_DAILY_EXECUTIVE_RECONCILER_V2.py") -Force

& $Python -c "import reportlab; print('REPORTLAB=PASS')"
if ($LASTEXITCODE -ne 0) { throw "ReportLab missing in this Python." }

$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($null -eq $gh) {
  Write-Warning "GitHub CLI (gh) not found. V2 will still use a local canonical QMASTER if present, but cannot sync it from gate-btc-runtime."
} else {
  & gh auth status 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "gh exists but is not authenticated. Run: gh auth login"
  }
}

$cmd = Join-Path $InstallDir "RUN_DAILY_EXECUTIVE_V2.cmd"
$pyfile = Join-Path $InstallDir "GATE_BTC_DAILY_EXECUTIVE_RECONCILER_V2.py"
@"
@echo off
"$Python" "$pyfile" >> "%USERPROFILE%\Downloads\GATE_BTC_DAILY_EXECUTIVE_TASK.log" 2>&1
"@ | Set-Content -Encoding ASCII $cmd

schtasks /Create /TN $TaskName /TR "`"$cmd`"" /SC DAILY /ST $DailyTime /F | Out-Host
schtasks /Run /TN $TaskName | Out-Host

Write-Host ""
Write-Host "INSTALLED=PASS" -ForegroundColor Green
Write-Host "VERSION=V2_CANONICAL_QMASTER"
Write-Host "TASK=$TaskName"
Write-Host "TIME=$DailyTime"
Write-Host "OUTPUT=$env:USERPROFILE\Downloads\GATE_BTC_DAILY_EXECUTIVE_LATEST.pdf"
Write-Host "STATE=$env:USERPROFILE\Downloads\GATE_BTC_DAILY_EXECUTIVE_LATEST.txt"
Write-Host "DISCOVERY=$env:USERPROFILE\Downloads\GATE_BTC_DAILY_EXECUTIVE_DISCOVERY.txt"
Write-Host "QMASTER_CACHE=$env:USERPROFILE\Downloads\GATE_BTC_QMASTER_LATEST.txt"
Write-Host "RESEARCH_ONLY=True | SHADOW_ONLY=True | NOT_APPROVED=True | ORDERS=0 | CAPITAL=0"
