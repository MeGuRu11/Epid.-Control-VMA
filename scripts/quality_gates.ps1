Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (Test-Path ".\venv\Scripts\python.exe") {
    $python = ".\venv\Scripts\python.exe"
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    $python = ".\.venv\Scripts\python.exe"
} else {
    $python = "python"
}

$env:EPIDCONTROL_DATA_DIR = Join-Path $repoRoot "tmp_run\epid-data"
$env:QT_QPA_PLATFORM = "offscreen"
$env:PYTHONUTF8 = "1"

Write-Host "Using Python interpreter: $python"
Write-Host "EPIDCONTROL_DATA_DIR: $env:EPIDCONTROL_DATA_DIR"

function Invoke-PythonStep {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & $python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $python $($Args -join ' ')"
    }
}

Invoke-PythonStep -Args @("-m", "ruff", "check", "app", "tests")
Invoke-PythonStep -Args @("scripts/check_architecture.py")
Invoke-PythonStep -Args @("-m", "mypy", "app", "tests")
Invoke-PythonStep -Args @("-m", "pytest", "-q")
Invoke-PythonStep -Args @("-m", "compileall", "-q", "app", "tests", "scripts")
Invoke-PythonStep -Args @("-m", "alembic", "upgrade", "head")
Invoke-PythonStep -Args @("-m", "alembic", "check")
Invoke-PythonStep -Args @("scripts/check_mojibake.py")

Write-Host ""
Write-Host "Quality gates passed: ruff, architecture, mypy, pytest, compileall, alembic, mojibake."
