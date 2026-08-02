@echo off
setlocal
title GATE BTC - Gateway Source Locator

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Find-GateBtcGatewaySource.ps1"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo Busca concluida. Envie ao ChatGPT o TXT GATE_BTC_GATEWAY_SOURCE_LOCATOR_*.txt criado em Downloads.
) else (
  echo A busca terminou com erro. Envie ao ChatGPT o TXT GATE_BTC_GATEWAY_SOURCE_LOCATOR_*.txt criado em Downloads.
)
echo.
pause
exit /b %RC%
