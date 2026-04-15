param(
    [string]$Version = "",
    [string]$Publisher = "MeGuRu11",
    [string]$AppName = "Epid Control VMA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "build_ui.ps1")

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$steps = @(
    "Определение версии приложения",
    "Проверка входных файлов",
    "Поиск компилятора Inno Setup",
    "Сборка Inno Setup установщика",
    "Проверка артефакта и финальная сводка"
)

Initialize-BuildUi -Activity "Сборка Inno Setup установщика" -Prefix "build-inno" -Steps $steps

try {
    if ([string]::IsNullOrWhiteSpace($Version)) {
        Start-BuildStep -Message "Определение версии приложения" -Emoji "[VERSION]"
        $Version = Get-ProjectVersion -Root $root -DefaultVersion "0.1.0"
        Write-BuildInfo ("Версия взята из pyproject.toml: {0}" -f $Version)
    } else {
        Start-BuildStep -Message "Определение версии приложения" -Emoji "[VERSION]"
        Write-BuildInfo ("Версия передана параметром: {0}" -f $Version)
    }

    $distExe = Join-Path $root "dist\EpidControl.exe"
    $issPath = Join-Path $root "scripts\installer.iss"
    $outputInstaller = Join-Path $root "dist\EpidControlSetup.exe"

    Start-BuildStep -Message "Проверка входных файлов" -Emoji "[CHECK]"
    if (-not (Test-Path $distExe)) {
        throw "Не найден входной файл $distExe. Сначала выполните scripts\\build_exe.bat."
    }
    if (-not (Test-Path $issPath)) {
        throw "Не найден сценарий Inno Setup: $issPath"
    }
    Write-BuildInfo ("EXE для упаковки: {0}" -f (Resolve-DisplayPath -Path $distExe))
    Write-BuildInfo ("Сценарий Inno Setup: {0}" -f (Resolve-DisplayPath -Path $issPath))

    Start-BuildStep -Message "Поиск компилятора Inno Setup" -Emoji "[DEPEND]"
    $iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    $isccPath = Resolve-ToolPath -CommandInfo $iscc
    if ([string]::IsNullOrWhiteSpace($isccPath)) {
        $default = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if (Test-Path $default) {
            $isccPath = $default
        }
    }

    if ([string]::IsNullOrWhiteSpace($isccPath)) {
        throw "ISCC.exe не найден. Установите Inno Setup 6 и добавьте его в PATH."
    }

    Write-BuildSuccess ("Используется ISCC: {0}" -f $isccPath)
    Write-BuildInfo ("Параметры: AppName='{0}', Publisher='{1}', Version='{2}'" -f $AppName, $Publisher, $Version)

    Start-BuildStep -Message "Сборка Inno Setup установщика" -Emoji "[BUILD]"
    $arguments = @(
        "/DMyAppVersion=$Version",
        "/DMyAppPublisher=$Publisher",
        "/DMyAppName=$AppName",
        $issPath
    )

    & $isccPath @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Компиляция Inno Setup завершилась с ошибкой."
    }

    Start-BuildStep -Message "Проверка артефакта и финальная сводка" -Emoji "[VERIFY]"
    if (-not (Test-Path $outputInstaller)) {
        throw "Ожидаемый установщик не найден: $outputInstaller"
    }

    Complete-BuildUi `
        -Message "Inno Setup установщик собран. Всё готово." `
        -Artifacts @(
            @{ Label = "Inno Setup installer"; Path = $outputInstaller },
            @{ Label = "Source EXE"; Path = $distExe }
        ) `
        -NextSteps @(
            "Проверьте установщик на чистом профиле Windows.",
            "После установки убедитесь, что мастер показывает финальное сообщение о готовности."
        )
    exit 0
} catch {
    Fail-BuildUi `
        -Message $_.Exception.Message `
        -Hints @(
            "Сначала соберите dist\\EpidControl.exe через scripts\\build_exe.bat.",
            "Проверьте установку Inno Setup 6 и наличие ISCC.exe в PATH.",
            "Если установщик не появился в dist, проверьте вывод компилятора выше."
        )
    exit 1
}
