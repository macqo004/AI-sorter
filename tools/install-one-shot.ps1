[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:USERPROFILE\AI-Sorter",
    [string]$RepoRef = "feature/application-foundation"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoOwner = "macqo004"
$RepoName = "AI-sorter"
$PythonVersion = "3.13.15"
$PythonInstallerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$VcRedistUrl = "https://aka.ms/vc14/vc_redist.x64.exe"
$RepoZipUrl = "https://codeload.github.com/$RepoOwner/$RepoName/zip/refs/heads/$RepoRef"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Download-File([string]$Url, [string]$Destination) {
    Write-Host "Downloading $Url" -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

try {
    if (-not $IsWindows) {
        throw "This installer is intended for Windows 10/11."
    }

    $InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
    $RuntimeRoot = Join-Path $InstallRoot "runtime"
    $PythonRoot = Join-Path $RuntimeRoot "python"
    $SourceRoot = Join-Path $InstallRoot "app\source"
    $ToolsRoot = Join-Path $InstallRoot "tools"
    $LauncherPath = Join-Path $InstallRoot "AI-Sorter.cmd"

    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

    Write-Step "Preparing portable directories"
    foreach ($Directory in @(
        $InstallRoot,
        $RuntimeRoot,
        (Join-Path $InstallRoot "app"),
        $SourceRoot,
        (Join-Path $InstallRoot "config"),
        (Join-Path $InstallRoot "data"),
        (Join-Path $InstallRoot "logs"),
        (Join-Path $InstallRoot "cache"),
        (Join-Path $InstallRoot "models"),
        (Join-Path $InstallRoot "modules"),
        (Join-Path $InstallRoot "backups"),
        (Join-Path $InstallRoot "temp"),
        $ToolsRoot
    )) {
        New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    }

    Write-Step "Downloading application source"
    $RepoZip = Join-Path $env:TEMP "AI-Sorter-$RepoRef.zip"
    Download-File -Url $RepoZipUrl -Destination $RepoZip

    $ExtractRoot = Join-Path $env:TEMP "AI-Sorter-install-$([guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
    Expand-Archive -Path $RepoZip -DestinationPath $ExtractRoot -Force

    $ExtractedRepo = Get-ChildItem -Path $ExtractRoot -Directory | Select-Object -First 1
    if (-not $ExtractedRepo) {
        throw "The downloaded application archive could not be located."
    }

    if (Test-Path $SourceRoot) {
        Remove-Item -Path $SourceRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $SourceRoot | Out-Null
    Copy-Item -Path (Join-Path $ExtractedRepo.FullName "src") -Destination $SourceRoot -Recurse -Force
    Copy-Item -Path (Join-Path $ExtractedRepo.FullName "pyproject.toml") -Destination $SourceRoot -Force

    Write-Step "Installing Python $PythonVersion locally"
    $PythonInstaller = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"
    Download-File -Url $PythonInstallerUrl -Destination $PythonInstaller

    if (-not (Test-Path (Join-Path $PythonRoot "python.exe"))) {
        $Arguments = @(
            "/quiet",
            "InstallAllUsers=0",
            "TargetDir=$PythonRoot",
            "Include_launcher=0",
            "Include_test=0",
            "Include_tcltk=0",
            "PrependPath=0",
            "AssociateFiles=0",
            "Shortcuts=0"
        )
        $Process = Start-Process -FilePath $PythonInstaller -ArgumentList $Arguments -Wait -PassThru
        if ($Process.ExitCode -ne 0) {
            throw "Python installer failed with exit code $($Process.ExitCode)."
        }
    }

    $PythonExe = Join-Path $PythonRoot "python.exe"
    if (-not (Test-Path $PythonExe)) {
        throw "Python installation completed without producing python.exe."
    }

    Write-Step "Installing Python dependencies"
    & $PythonExe -m pip install --disable-pip-version-check --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip installation failed." }

    & $PythonExe -m pip install --disable-pip-version-check (Join-Path $SourceRoot "")
    if ($LASTEXITCODE -ne 0) { throw "AI-Sorter package installation failed." }

    Write-Step "Creating launcher"
    @"
@echo off
set "AI_SORTER_HOME=$InstallRoot"
set "PYTHONPATH=$SourceRoot\src"
"$PythonExe" -m ai_sorter
if errorlevel 1 (
    echo.
    echo AI-Sorter could not start. Check the logs directory for technical details.
    pause
)
"@ | Set-Content -Path $LauncherPath -Encoding ASCII

    Write-Step "Writing installation metadata"
    @"
AI-Sorter portable installation
Repository: $RepoOwner/$RepoName
Revision: $RepoRef
Python: $PythonVersion
Installed: $(Get-Date -Format s)
InstallRoot: $InstallRoot
"@ | Set-Content -Path (Join-Path $InstallRoot "INSTALLATION.txt") -Encoding UTF8

    Remove-Item -Path $RepoZip -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $ExtractRoot -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "`nInstallation complete." -ForegroundColor Green
    Write-Host "Location: $InstallRoot"
    Write-Host "Launcher: $LauncherPath"
    Write-Host "`nNote: this bootstrap requires Internet access during installation."

    & $LauncherPath
}
catch {
    Write-Host "`nINSTALLATION FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nNo image collection files are modified by this installer."
    exit 1
}
