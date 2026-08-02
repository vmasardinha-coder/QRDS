@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "VERIFY_PS1=%SCRIPT_DIR%Invoke-GateBtcLocalVerify.ps1"

if not exist "%VERIFY_PS1%" (
  echo ERROR: Missing verifier script: %VERIFY_PS1%
  pause
  exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%VERIFY_PS1%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo GATE BTC verification completed successfully.
  echo Send the generated GATE_BTC_WINDOWS_LOCAL_VERIFY_*.txt from Downloads to the chat.
) else (
  echo GATE BTC verification finished with an error.
  echo Send the generated GATE_BTC_WINDOWS_LOCAL_VERIFY_*.txt from Downloads to the chat.
)

pause
exit /b %RC%
