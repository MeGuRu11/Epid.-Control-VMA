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
    Write-Host "[build-inno] $Message" -ForegroundColor Cyan
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
$issPath = Join-Path $root "scripts\installer.iss"

if (-not (Test-Path $distExe)) {
    throw "Required file not found: $distExe. Build executable first (scripts\\build_exe.bat)."
}

if (-not (Test-Path $issPath)) {
    throw "Inno Setup script not found: $issPath"
}

$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if (-not $iscc) {
    $default = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $default) {
        $iscc = Get-Item $default
    }
}

if (-not $iscc) {
    throw "ISCC.exe was not found. Install Inno Setup and add it to PATH."
}

Write-Step "Using ISCC: $($iscc.FullName)"
Write-Step "Version: $Version"

$arguments = @(
    "/DMyAppVersion=$Version",
    "/DMyAppPublisher=$Publisher",
    "/DMyAppName=$AppName",
    $issPath
)

& $iscc.FullName @arguments

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed."
}

Write-Step "Installer created in dist/ (OutputBaseFilename from installer.iss)."
