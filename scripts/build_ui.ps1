Set-StrictMode -Version Latest

function Get-ProjectVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [string]$DefaultVersion = "0.1.0"
    )

    $pyproject = Join-Path $Root "pyproject.toml"
    if (-not (Test-Path $pyproject)) {
        return $DefaultVersion
    }

    $line = Select-String -Path $pyproject -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $line) {
        return $DefaultVersion
    }

    return $line.Matches[0].Groups[1].Value
}

function Resolve-ToolPath {
    param([object]$CommandInfo)

    if ($null -eq $CommandInfo) {
        return $null
    }

    foreach ($propertyName in @("Source", "Path", "FullName", "Definition")) {
        $property = $CommandInfo.PSObject.Properties[$propertyName]
        if ($null -ne $property -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            return [string]$property.Value
        }
    }

    return $null
}

function Resolve-DisplayPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        return (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    } catch {
        return [System.IO.Path]::GetFullPath($Path)
    }
}

function Initialize-BuildUi {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Activity,
        [Parameter(Mandatory = $true)]
        [string]$Prefix,
        [Parameter(Mandatory = $true)]
        [string[]]$Steps
    )

    $script:BuildUiState = @{
        Activity    = $Activity
        Prefix      = $Prefix
        Steps       = $Steps
        TotalSteps  = $Steps.Count
        CurrentStep = 0
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host ("[PACKAGE] {0}" -f $Activity) -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkCyan
}

function Get-ProgressBar {
    param([int]$Percent)

    $width = 24
    $filled = [Math]::Floor(($Percent / 100) * $width)
    $empty = $width - $filled
    return ("#" * $filled) + ("-" * $empty)
}

function Start-BuildStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string]$Emoji = "[STEP]"
    )

    $script:BuildUiState.CurrentStep += 1
    $totalSteps = [Math]::Max([int]$script:BuildUiState.TotalSteps, 1)
    $currentStep = [int]$script:BuildUiState.CurrentStep
    $percent = [Math]::Min([int](($currentStep - 1) * 100 / $totalSteps), 99)
    $bar = Get-ProgressBar -Percent $percent
    $status = "Шаг $currentStep/$totalSteps - $Message"

    Write-Progress -Activity $script:BuildUiState.Activity -Status $status -PercentComplete $percent
    Write-Host ("{0} [{1}] {2,3}%  {3}" -f $Emoji, $bar, $percent, $status) -ForegroundColor Cyan
}

function Write-BuildInfo {
    param([string]$Message)
    Write-Host ("[INFO] {0}" -f $Message) -ForegroundColor Gray
}

function Write-BuildSuccess {
    param([string]$Message)
    Write-Host ("[OK] {0}" -f $Message) -ForegroundColor Green
}

function Write-BuildWarning {
    param([string]$Message)
    Write-Host ("[WARN] {0}" -f $Message) -ForegroundColor Yellow
}

function Complete-BuildUi {
    param(
        [string]$Message = "Всё готово.",
        [object[]]$Artifacts = @(),
        [string[]]$NextSteps = @()
    )

    Write-Progress -Activity $script:BuildUiState.Activity -Completed
    Write-Host ("[DONE] {0}" -f $Message) -ForegroundColor Green

    if ($Artifacts.Count -gt 0) {
        Write-Host ""
        Write-Host "Созданные артефакты:" -ForegroundColor DarkGreen
        foreach ($artifact in $Artifacts) {
            if ($artifact -is [hashtable]) {
                $label = [string]$artifact.Label
                $path = Resolve-DisplayPath -Path ([string]$artifact.Path)
                Write-Host ("  - {0}: {1}" -f $label, $path) -ForegroundColor Green
            }
        }
    }

    if ($NextSteps.Count -gt 0) {
        Write-Host ""
        Write-Host "Следующие шаги:" -ForegroundColor DarkCyan
        foreach ($step in $NextSteps) {
            Write-Host ("  - {0}" -f $step) -ForegroundColor Cyan
        }
    }
}

function Fail-BuildUi {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string[]]$Hints = @()
    )

    Write-Progress -Activity $script:BuildUiState.Activity -Completed
    Write-Host ("[ERROR] {0}" -f $Message) -ForegroundColor Red

    if ($Hints.Count -gt 0) {
        Write-Host ""
        Write-Host "Что проверить:" -ForegroundColor Yellow
        foreach ($hint in $Hints) {
            Write-Host ("  - {0}" -f $hint) -ForegroundColor Yellow
        }
    }
}
