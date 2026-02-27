param(
    [string]$Version = "",
    [string]$Publisher = "MeGuRu11",
    [string]$AppName = "Epid Control VMA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
    param([string]$Message)
    Write-Host "[build-nsis] $Message" -ForegroundColor Cyan
}

function Get-ProjectVersion {
    param([string]$Root)

    $pyproject = Join-Path $Root "pyproject.toml"
    if (-not (Test-Path $pyproject)) {
        return "0.1.0"
    }

    $line = Select-String -Path $pyproject -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $line) {
        return "0.1.0"
    }

    return $line.Matches[0].Groups[1].Value
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Get-ProjectVersion -Root $root
}

$distExe = Join-Path $root "dist\EpidControl.exe"
$nsiPath = Join-Path $root "scripts\installer.nsi"
$outputInstaller = Join-Path $root "dist\EpidControlSetup_NSIS.exe"

if (-not (Test-Path $distExe)) {
    throw "Required file not found: $distExe. Build executable first (scripts\\build_exe.bat)."
}

if (-not (Test-Path $nsiPath)) {
    throw "NSIS script not found: $nsiPath"
}

$makensis = Get-Command "makensis.exe" -ErrorAction SilentlyContinue
if (-not $makensis) {
    $default = "C:\Program Files (x86)\NSIS\makensis.exe"
    if (Test-Path $default) {
        $makensis = Get-Item $default
    }
}

if (-not $makensis) {
    throw "makensis.exe was not found. Install NSIS and add it to PATH."
}

Write-Step "Using makensis: $($makensis.FullName)"
Write-Step "Version: $Version"

$arguments = @(
    "/DAPP_VERSION=$Version",
    "/DAPP_PUBLISHER=$Publisher",
    "/DAPP_NAME=$AppName",
    $nsiPath
)

& $makensis.FullName @arguments

if ($LASTEXITCODE -ne 0) {
    throw "NSIS compilation failed."
}

if (-not (Test-Path $outputInstaller)) {
    throw "Installer output not found: $outputInstaller"
}

Write-Step "Installer created: $outputInstaller"
