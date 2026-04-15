@echo off
setlocal
cd /d "%~dp0\.."
chcp 65001 >nul

echo ============================================================
echo Epid Control VMA - Windows EXE build
echo ============================================================
echo [1/2] Starting PowerShell build script...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 %*
if errorlevel 1 (
  echo.
  echo [EpidControl] FAIL: EXE build finished with an error.
  exit /b 1
)

echo [2/2] PowerShell script finished without errors.
echo [EpidControl] DONE: Everything is ready.
endlocal
