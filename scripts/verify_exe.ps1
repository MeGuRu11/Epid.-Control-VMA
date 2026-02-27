Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$dist = Join-Path $root "dist"
$exe = Join-Path $dist "EpidControl.exe"
$releaseInfo = Join-Path $dist "RELEASE_INFO.txt"

if (-not (Test-Path $exe)) {
    Write-Host "Missing executable: $exe" -ForegroundColor Red
    exit 1
}

$exeInfo = Get-Item $exe
Write-Host "Executable found: $exe"
Write-Host ("Size: {0:N0} bytes" -f $exeInfo.Length)

$internal = Join-Path $dist "_internal"
if (Test-Path $internal) {
    $pythonDll = Get-ChildItem -Path $internal -Filter "python3*.dll" -File | Select-Object -First 1
    if (-not $pythonDll) {
        Write-Host "Warning: no python3*.dll found in $internal" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Runtime DLL found: $($pythonDll.Name)"
}

if (Test-Path $releaseInfo) {
    Write-Host "Release metadata found: $releaseInfo"
} else {
    Write-Host "Warning: RELEASE_INFO.txt was not found in dist/." -ForegroundColor Yellow
}

Write-Host "EXE verification passed." -ForegroundColor Green
