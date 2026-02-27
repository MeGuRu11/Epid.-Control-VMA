param(
    [switch]$SkipClean,
    [switch]$SkipVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
    param([string]$Message)
    Write-Host "[build-exe] $Message" -ForegroundColor Cyan
}

function Get-ProjectVersion {
    param([string]$Root)

    $pyproject = Join-Path $Root "pyproject.toml"
    if (-not (Test-Path $pyproject)) {
        return "unknown"
    }

    $line = Select-String -Path $pyproject -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $line) {
        return "unknown"
    }

    return $line.Matches[0].Groups[1].Value
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$specPath = Join-Path $root "EpidControl.spec"
$distDir = Join-Path $root "dist"
$buildDir = Join-Path $root "build"
$exePath = Join-Path $distDir "EpidControl.exe"
$verifyScript = Join-Path $root "scripts\verify_exe.ps1"

Write-Step "Project root: $root"

if (-not (Test-Path $specPath)) {
    throw "PyInstaller spec file not found: $specPath"
}

$python = if (Test-Path ".\venv\Scripts\python.exe") {
    ".\venv\Scripts\python.exe"
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Step "Using Python: $python"

& $python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed in the selected interpreter. Install requirements-dev.txt first."
}

if (-not $SkipClean) {
    Write-Step "Cleaning previous build artifacts (build/, dist/)"
    if (Test-Path $buildDir) {
        Remove-Item -Recurse -Force $buildDir
    }
    if (Test-Path $distDir) {
        Remove-Item -Recurse -Force $distDir
    }
}

Write-Step "Running PyInstaller..."
& $python -m PyInstaller --noconfirm --clean EpidControl.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if (-not (Test-Path $exePath)) {
    throw "Build finished, but executable was not found: $exePath"
}

$version = Get-ProjectVersion -Root $root
$buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
$releaseInfoPath = Join-Path $distDir "RELEASE_INFO.txt"

@"
Epid Control VMA
Version: $version
Build time: $buildTime
Executable: $exePath
"@ | Set-Content -Path $releaseInfoPath -Encoding UTF8

Write-Step "Release metadata written: $releaseInfoPath"

if (-not $SkipVerify) {
    if (-not (Test-Path $verifyScript)) {
        throw "Verification script not found: $verifyScript"
    }

    Write-Step "Running executable verification..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyScript
    if ($LASTEXITCODE -ne 0) {
        throw "Executable verification failed."
    }
}

Write-Step "Build complete: $exePath"
