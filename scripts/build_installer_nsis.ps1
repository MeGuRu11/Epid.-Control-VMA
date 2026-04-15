param(
    [string]$Version = "",
    [string]$Publisher = "MeGuRu11",
    [string]$AppName = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "build_ui.ps1")

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$steps = @(
    "Определение версии приложения",
    "Проверка входных файлов",
    "Поиск компилятора NSIS",
    "Сборка NSIS установщика",
    "Проверка артефакта и финальная сводка"
)

Initialize-BuildUi -Activity "Сборка NSIS установщика" -Prefix "build-nsis" -Steps $steps

try {
    Start-BuildStep -Message "Определение версии приложения" -Emoji "[VERSION]"
    if ([string]::IsNullOrWhiteSpace($Version)) {
        $Version = Get-ProjectVersion -Root $root -DefaultVersion "0.1.0"
        Write-BuildInfo ("Версия взята из pyproject.toml: {0}" -f $Version)
    } else {
        Write-BuildInfo ("Версия передана параметром: {0}" -f $Version)
    }

    $distExe = Join-Path $root "dist\EpidControl.exe"
    $nsiPath = Join-Path $root "scripts\installer.nsi"
    $outputInstaller = Join-Path $root "dist\EpidControlSetup_NSIS.exe"

    Start-BuildStep -Message "Проверка входных файлов" -Emoji "[CHECK]"
    if (-not (Test-Path $distExe)) {
        throw "Не найден входной файл $distExe. Сначала выполните scripts\\build_exe.bat."
    }
    if (-not (Test-Path $nsiPath)) {
        throw "Не найден NSIS-сценарий: $nsiPath"
    }
    Write-BuildInfo ("EXE для упаковки: {0}" -f (Resolve-DisplayPath -Path $distExe))
    Write-BuildInfo ("Сценарий NSIS: {0}" -f (Resolve-DisplayPath -Path $nsiPath))

    Start-BuildStep -Message "Поиск компилятора NSIS" -Emoji "[DEPEND]"
    $makensis = Get-Command "makensis.exe" -ErrorAction SilentlyContinue
    $makensisPath = Resolve-ToolPath -CommandInfo $makensis
    if ([string]::IsNullOrWhiteSpace($makensisPath)) {
        $default = "C:\Program Files (x86)\NSIS\makensis.exe"
        if (Test-Path $default) {
            $makensisPath = $default
        }
    }

    if ([string]::IsNullOrWhiteSpace($makensisPath)) {
        throw "makensis.exe не найден. Установите NSIS и добавьте его в PATH."
    }

    Write-BuildSuccess ("Используется makensis: {0}" -f $makensisPath)
    if (-not [string]::IsNullOrWhiteSpace($AppName)) {
        Write-BuildInfo ("Переопределённое имя приложения: {0}" -f $AppName)
    }

    Start-BuildStep -Message "Сборка NSIS установщика" -Emoji "[BUILD]"
    $arguments = @(
        "/INPUTCHARSET",
        "UTF8",
        "/DAPP_VERSION=$Version",
        "/DAPP_PUBLISHER=$Publisher",
        $nsiPath
    )

    if (-not [string]::IsNullOrWhiteSpace($AppName)) {
        $arguments = @("/DAPP_NAME=$AppName") + $arguments
    }

    & $makensisPath @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Компиляция NSIS завершилась с ошибкой."
    }

    Start-BuildStep -Message "Проверка артефакта и финальная сводка" -Emoji "[VERIFY]"
    if (-not (Test-Path $outputInstaller)) {
        throw "Ожидаемый NSIS-установщик не найден: $outputInstaller"
    }

    Complete-BuildUi `
        -Message "NSIS установщик собран. Всё готово." `
        -Artifacts @(
            @{ Label = "NSIS installer"; Path = $outputInstaller },
            @{ Label = "Source EXE"; Path = $distExe }
        ) `
        -NextSteps @(
            "Запустите установщик и проверьте приветственную и финальную страницы.",
            "После установки убедитесь, что приложение можно запустить с финальной страницы мастера."
        )
    exit 0
} catch {
    Fail-BuildUi `
        -Message $_.Exception.Message `
        -Hints @(
            "Сначала соберите dist\\EpidControl.exe через scripts\\build_exe.bat.",
            "Проверьте установку NSIS и наличие makensis.exe в PATH.",
            "Если установщик не появился в dist, проверьте сообщения компилятора выше."
        )
    exit 1
}
