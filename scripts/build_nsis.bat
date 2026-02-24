@echo off
setlocal
cd /d "%~dp0\.."
powershell -ExecutionPolicy Bypass -File scripts\build_installer_nsis.ps1
endlocal
