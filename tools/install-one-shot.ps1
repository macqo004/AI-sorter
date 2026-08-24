[CmdletBinding()]
param(
    [string]$InstallRoot,
    [string]$RepoRef = "feature/application-foundation"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoOwner = "macqo004"
$RepoName = "AI-sorter"
$PythonVersion = "3.13.15"
$PythonInstallerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$VcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$RepoZipUrl = "https://codeload.github.com/$RepoOwner/$RepoName/zip/refs/heads/$RepoRef"
$SafeRefName = ($RepoRef -replace '[^A-Za-z0-9._-]', '_')
$InstallerStateDir = Join-Path $env:LOCALAPPDATA "AI-Sorter"
$InstallerStatePath = Join-Path $InstallerStateDir "last-install-path.txt"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Download-File([string]$Url, [string]$Destination) {
    Write-Host "Downloading $Url" -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
    if (-not (Test-Path $Destination)) {
        throw "Download completed without creating the expected file: $Destination"
    }
}

function Get-LastInstallRoot {
    if (-not (Test-Path $InstallerStatePath)) {
        return $null
    }
    try {
        $value = (Get-Content -Path $InstallerStatePath -Raw -ErrorAction Stop).Trim()
        if ([string]::IsNullOrWhiteSpace($value)) {
            return $null
        }
        return $value
    }
    catch {
        return $null
    }
}

function Save-LastInstallRoot([string]$Path) {
    try {
        New-Item -ItemType Directory -Force -Path $InstallerStateDir | Out-Null
        Set-Content -Path $InstallerStatePath -Value $Path -Encoding UTF8
    }
    catch {
        Write-Host "Could not save the last installation path. The installation itself will continue." -ForegroundColor Yellow
    }
}

function Select-InstallRoot([string]$InitialPath) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Choose the folder where AI-Sorter will be installed."
    $dialog.ShowNewFolderButton = $true
    if (-not [string]::IsNullOrWhiteSpace($InitialPath)) {
        $dialog.SelectedPath = $InitialPath
    }
    else {
        $dialog.SelectedPath = Join-Path $env:USERPROFILE "AI-Sorter"
    }
    $result = $dialog.ShowDialog()
    if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
        throw "Installation was cancelled because no destination folder was selected."
    }
    return $dialog.SelectedPath
}

function Test-VcRedistX64Installed {
    $registryPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    foreach ($registryPath in $registryPaths) {
        try {
            $entries = Get-ItemProperty -Path $registryPath -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.DisplayName -and
                    $_.DisplayName -match 'Microsoft Visual C\+\+.*Redistributable' -and
                    $_.DisplayName -match '2015.*2022|2015-2022' -and
                    ($_.DisplayName -match '\(x64\)' -or $_.DisplayName -match 'x64')
                }
            if ($entries) {
                return $true
            }
        }
        catch {
            # Registry inspection is only a convenience check. The installer below remains authoritative.
        }
    }
    return $false
}

try {
    if ($env:OS -ne "Windows_NT") {
        throw "This installer is intended for Windows 10/11."
    }

    $LastInstallRoot = Get-LastInstallRoot

    if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
        Write-Step "Choose installation location"
        Write-Host "You can paste the full installation path below." -ForegroundColor DarkGray
        if ($LastInstallRoot) {
            Write-Host "Press ENTER to reuse the last location:" -ForegroundColor DarkGray
            Write-Host "  $LastInstallRoot" -ForegroundColor Green
        }
        else {
            Write-Host "Press ENTER to use the default location:" -ForegroundColor DarkGray
            Write-Host "  $(Join-Path $env:USERPROFILE 'AI-Sorter')" -ForegroundColor Green
        }

        $ManualPath = Read-Host "Installation path"
        if (-not [string]::IsNullOrWhiteSpace($ManualPath)) {
            $InstallRoot = $ManualPath.Trim().Trim('"')
        }
        elseif ($LastInstallRoot) {
            $InstallRoot = $LastInstallRoot
        }
        else {
            $InstallRoot = Join-Path $env:USERPROFILE "AI-Sorter"
        }

        if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
            Write-Host "Manual path entry was empty. Opening folder browser..." -ForegroundColor Yellow
            $InstallRoot = Select-InstallRoot -InitialPath $LastInstallRoot
        }
    }

    if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
        throw "No installation location was provided."
    }

    $InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
    Save-LastInstallRoot -Path $InstallRoot

    $RuntimeRoot = Join-Path $InstallRoot "runtime"
    $PythonRoot = Join-Path $RuntimeRoot "python"
    $SourceRoot = Join-Path $InstallRoot "app\source"
    $LauncherPath = Join-Path $InstallRoot "AI-Sorter.cmd"
    $InstallerLog = Join-Path $InstallRoot "installer-error.log"

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
        (Join-Path $InstallRoot "temp")
    )) {
        New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    }

    Write-Step "Downloading application source"
    $RepoZip = Join-Path $env:TEMP "AI-Sorter-$SafeRefName.zip"
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

    Write-Step "Checking Microsoft Visual C++ runtime"
    if (Test-VcRedistX64Installed) {
        Write-Host "Microsoft Visual C++ Runtime x64 is already installed. Skipping installation." -ForegroundColor Green
    }
    else {
        Write-Host "Microsoft Visual C++ Runtime x64 was not detected. Installing it now." -ForegroundColor DarkGray
        $VcInstaller = Join-Path $env:TEMP "vc_redist.x64.exe"
        Download-File -Url $VcRedistUrl -Destination $VcInstaller
        $VcProcess = Start-Process -FilePath $VcInstaller -ArgumentList "/install", "/quiet", "/norestart" -Wait -PassThru
        switch ($VcProcess.ExitCode) {
            0 {
                Write-Host "Microsoft Visual C++ Runtime installed successfully." -ForegroundColor Green
            }
            1638 {
                Write-Host "Microsoft Visual C++ Runtime was already installed by another package or version. Continuing." -ForegroundColor Green
            }
            3010 {
                Write-Host "Microsoft Visual C++ Runtime installed successfully. Windows reports that a restart may be required; continuing without reboot." -ForegroundColor Yellow
            }
            default {
                throw "Microsoft Visual C++ runtime installation failed with exit code $($VcProcess.ExitCode)."
            }
        }
    }

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
    & $PythonExe -m pip install --disable-pip-version-check --upgrade pip setuptools
    if ($LASTEXITCODE -ne 0) { throw "pip/setuptools installation failed." }

    & $PythonExe -m pip install --disable-pip-version-check $SourceRoot
    if ($LASTEXITCODE -ne 0) { throw "AI-Sorter package installation failed." }

    Write-Step "Creating launcher"
    @"
@echo off
setlocal
set "AI_SORTER_HOME=$InstallRoot"
set "PYTHONPATH=$SourceRoot\src"
"$PythonExe" -m ai_sorter
if errorlevel 1 (
    echo.
    echo AI-Sorter could not start. Check the logs directory for technical details.
    pause
)
endlocal
"@ | Set-Content -Path $LauncherPath -Encoding ASCII

    @"
AI-Sorter portable installation
Repository: $RepoOwner/$RepoName
Revision: $RepoRef
Python: $PythonVersion
Installed: $(Get-Date -Format s)
InstallRoot: $InstallRoot
Last-path state: $InstallerStatePath
"@ | Set-Content -Path (Join-Path $InstallRoot "INSTALLATION.txt") -Encoding UTF8

    Remove-Item -Path $RepoZip -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $ExtractRoot -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "`nInstallation complete." -ForegroundColor Green
    Write-Host "Location: $InstallRoot"
    Write-Host "Launcher: $LauncherPath"
    Write-Host "Last installation path is remembered for the next run."
    Write-Host "You can also paste a different path next time."
    Write-Host "`nThis bootstrap requires Internet access during installation."

    Start-Process -FilePath $LauncherPath
}
catch {
    $Message = $_.Exception.Message
    try {
        if ($InstallRoot) {
            @"
AI-Sorter installer failure
Time: $(Get-Date -Format s)
Repository: $RepoOwner/$RepoName
Revision: $RepoRef
Error: $Message

Technical details:
$($_ | Out-String)
"@ | Set-Content -Path $InstallerLog -Encoding UTF8
        }
    }
    catch {
        # Preserve the original error if logging itself fails.
    }

    Write-Host "`nINSTALLATION FAILED" -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    if ($InstallRoot) {
        Write-Host "`nInstaller log: $InstallerLog" -ForegroundColor Yellow
    }
    Write-Host "`nNo image collection files are modified by this installer." -ForegroundColor Yellow
    Read-Host "Press ENTER to close"
    exit 1
}
