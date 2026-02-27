@echo off
setlocal
cd /d "%~dp0\.."

echo [EpidControl] Building NSIS installer...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_installer_nsis.ps1 %*
if errorlevel 1 (
  echo [EpidControl] NSIS build failed.
  exit /b 1
)

echo [EpidControl] NSIS installer completed successfully.
endlocal
