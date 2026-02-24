$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$dist = Join-Path $root "dist"
$exe = Join-Path $dist "EpidControl.exe"

if (-not (Test-Path $exe)) {
    Write-Host "Не найден: $exe" -ForegroundColor Red
    exit 1
}

$internal = Join-Path $dist "_internal"
if (Test-Path $internal) {
    $dll = Join-Path $internal "python312.dll"
    if (-not (Test-Path $dll)) {
        Write-Host "Предупреждение: не найден python312.dll в $internal" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "OK: $exe" -ForegroundColor Green
