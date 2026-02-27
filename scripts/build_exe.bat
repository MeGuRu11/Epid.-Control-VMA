@echo off
setlocal
cd /d "%~dp0\.."

echo [EpidControl] Building Windows executable...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1 %*
if errorlevel 1 (
  echo [EpidControl] Build failed.
  exit /b 1
)

echo [EpidControl] Build completed successfully.
endlocal
