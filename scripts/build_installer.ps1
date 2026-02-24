$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if (-not $iscc) {
    $default = "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
    if (Test-Path $default) {
        $iscc = Get-Item $default
    }
}

if (-not $iscc) {
    $hint = '"{0}" "scripts\\installer.iss"' -f "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
    Write-Host "ISCC.exe не найден. Установите Inno Setup и добавьте ISCC.exe в PATH." -ForegroundColor Yellow
    Write-Host ("Либо запустите: {0}" -f $hint) -ForegroundColor Yellow
    exit 1
}

& $iscc.FullName "scripts\\installer.iss"
