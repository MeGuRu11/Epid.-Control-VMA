$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$makensis = Get-Command "makensis.exe" -ErrorAction SilentlyContinue
if (-not $makensis) {
    $default = "C:\\Program Files (x86)\\NSIS\\makensis.exe"
    if (Test-Path $default) {
        $makensis = Get-Item $default
    }
}

if (-not $makensis) {
    $hint = '"{0}" "scripts\\installer.nsi"' -f "C:\\Program Files (x86)\\NSIS\\makensis.exe"
    Write-Host "makensis.exe не найден. Установите NSIS и добавьте makensis.exe в PATH." -ForegroundColor Yellow
    Write-Host ("Либо запустите: {0}" -f $hint) -ForegroundColor Yellow
    exit 1
}

& $makensis.FullName (Join-Path $root "scripts\\installer.nsi")
