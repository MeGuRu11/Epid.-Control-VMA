@echo off
setlocal
cd /d "%~dp0\.."
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
endlocal
