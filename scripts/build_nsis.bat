@echo off
setlocal
cd /d "%~dp0\.."
chcp 65001 >nul

echo ============================================================
echo Epid Control VMA - NSIS installer build
echo ============================================================
echo [1/2] Starting PowerShell packaging script...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_installer_nsis.ps1 %*
if errorlevel 1 (
  echo.
  echo [EpidControl] FAIL: NSIS installer build finished with an error.
  exit /b 1
)

echo [2/2] PowerShell script finished without errors.
echo [EpidControl] DONE: Everything is ready.
endlocal
