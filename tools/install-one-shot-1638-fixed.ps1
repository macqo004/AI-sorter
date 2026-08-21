[CmdletBinding()]
param([string]$InstallRoot)
$ErrorActionPreference='Stop'
$PythonVersion='3.13.15'
$VcRedistUrl='https://aka.ms/vs/17/release/vc_redist.x64.exe'
$RepoRef='feature/application-foundation'
$RepoZipUrl="https://codeload.github.com/macqo004/AI-sorter/zip/refs/heads/$RepoRef"
# TEMP installer variant used only to verify the VC++ handling fix.
$Root = if ($InstallRoot) {[IO.Path]::GetFullPath($InstallRoot)} else {$env:USERPROFILE + '\AI-Sorter'}
New-Item -ItemType Directory -Force $Root | Out-Null
$VcInstaller=Join-Path $env:TEMP 'vc_redist.x64.exe'
Invoke-WebRequest -Uri $VcRedistUrl -OutFile $VcInstaller -UseBasicParsing
$p=Start-Process -FilePath $VcInstaller -ArgumentList '/install','/quiet','/norestart' -Wait -PassThru
if ($p.ExitCode -notin @(0,1638,3010)) { throw "Microsoft Visual C++ runtime installation failed with exit code $($p.ExitCode)." }
if ($p.ExitCode -eq 1638) { Write-Host 'Microsoft Visual C++ runtime is already installed. Continuing.' -ForegroundColor Yellow }
elseif ($p.ExitCode -eq 3010) { Write-Host 'Microsoft Visual C++ runtime is installed. A restart may be required; continuing.' -ForegroundColor Yellow }
Write-Host 'VC++ prerequisite check passed.' -ForegroundColor Green
