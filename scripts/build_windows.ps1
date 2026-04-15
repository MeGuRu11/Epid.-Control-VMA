param(
    [switch]$SkipClean,
    [switch]$SkipVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "build_ui.ps1")

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$steps = @(
    "Проверка структуры проекта",
    "Поиск интерпретатора Python",
    "Проверка зависимости PyInstaller"
)
if (-not $SkipClean) {
    $steps += "Очистка прошлых артефактов"
}
$steps += "Сборка EXE через PyInstaller"
$steps += "Подготовка release metadata"
if (-not $SkipVerify) {
    $steps += "Проверка собранного EXE"
}

Initialize-BuildUi -Activity "Сборка Windows EXE" -Prefix "build-exe" -Steps $steps

try {
    $specPath = Join-Path $root "EpidControl.spec"
    $distDir = Join-Path $root "dist"
    $buildDir = Join-Path $root "build"
    $exePath = Join-Path $distDir "EpidControl.exe"
    $verifyScript = Join-Path $root "scripts\verify_exe.ps1"

    Start-BuildStep -Message "Проверка структуры проекта" -Emoji "[CHECK]"
    if (-not (Test-Path $specPath)) {
        throw "Не найден PyInstaller spec-файл: $specPath"
    }
    Write-BuildInfo ("Корень проекта: {0}" -f (Resolve-DisplayPath -Path $root))
    Write-BuildInfo ("Spec-файл: {0}" -f (Resolve-DisplayPath -Path $specPath))

    Start-BuildStep -Message "Поиск интерпретатора Python" -Emoji "[PYTHON]"
    $python = if (Test-Path ".\venv\Scripts\python.exe") {
        ".\venv\Scripts\python.exe"
    } elseif (Test-Path ".\.venv\Scripts\python.exe") {
        ".\.venv\Scripts\python.exe"
    } else {
        "python"
    }
    Write-BuildInfo ("Интерпретатор: {0}" -f $python)

    Start-BuildStep -Message "Проверка зависимости PyInstaller" -Emoji "[DEPEND]"
    & $python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller не найден в выбранном интерпретаторе. Установите зависимости из requirements-dev.txt."
    }
    Write-BuildSuccess "PyInstaller доступен."

    if (-not $SkipClean) {
        Start-BuildStep -Message "Очистка прошлых артефактов" -Emoji "[CLEAN]"
        if (Test-Path $buildDir) {
            Remove-Item -Recurse -Force $buildDir
        }
        if (Test-Path $distDir) {
            Remove-Item -Recurse -Force $distDir
        }
        Write-BuildSuccess "Каталоги build/ и dist/ очищены."
    }

    Start-BuildStep -Message "Сборка EXE через PyInstaller" -Emoji "[BUILD]"
    & $python -m PyInstaller --noconfirm --clean $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller завершился с ошибкой."
    }
    if (-not (Test-Path $exePath)) {
        throw "Сборка завершилась без ошибки, но файл EXE не найден: $exePath"
    }
    Write-BuildSuccess ("EXE собран: {0}" -f (Resolve-DisplayPath -Path $exePath))

    Start-BuildStep -Message "Подготовка release metadata" -Emoji "[META]"
    $version = Get-ProjectVersion -Root $root -DefaultVersion "unknown"
    $buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $releaseInfoPath = Join-Path $distDir "RELEASE_INFO.txt"

    @"
Epid Control VMA
Version: $version
Build time: $buildTime
Executable: $exePath
"@ | Set-Content -Path $releaseInfoPath -Encoding UTF8

    Write-BuildSuccess ("Файл RELEASE_INFO.txt создан: {0}" -f (Resolve-DisplayPath -Path $releaseInfoPath))

    if (-not $SkipVerify) {
        Start-BuildStep -Message "Проверка собранного EXE" -Emoji "[VERIFY]"
        if (-not (Test-Path $verifyScript)) {
            throw "Не найден скрипт проверки EXE: $verifyScript"
        }

        & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyScript
        if ($LASTEXITCODE -ne 0) {
            throw "Проверка EXE завершилась с ошибкой."
        }
        Write-BuildSuccess "Проверка EXE успешно завершена."
    } else {
        Write-BuildWarning "Пост-проверка EXE пропущена из-за параметра -SkipVerify."
    }

    $artifacts = @(
        @{ Label = "EXE"; Path = $exePath },
        @{ Label = "Release metadata"; Path = $releaseInfoPath }
    )
    Complete-BuildUi `
        -Message "Сборка Windows EXE завершена. Всё готово." `
        -Artifacts $artifacts `
        -NextSteps @(
            "Для NSIS-установщика: scripts\\build_nsis.bat",
            "Для Inno Setup: powershell -ExecutionPolicy Bypass -File scripts\\build_installer.ps1"
        )
    exit 0
} catch {
    Fail-BuildUi `
        -Message $_.Exception.Message `
        -Hints @(
            "Проверьте наличие зависимостей из requirements-dev.txt.",
            "Убедитесь, что dist\\EpidControl.exe не открыт другой программой.",
            "Если проблема в окружении, повторите запуск из активированного venv."
        )
    exit 1
}
