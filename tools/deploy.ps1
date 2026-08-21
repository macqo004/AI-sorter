[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot '.venv'

Write-Host 'AI-Sorter deployment/bootstrap' -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"

$directories = @(
    'app',
    'config',
    'data',
    'logs',
    'cache',
    'models',
    'modules',
    'backups',
    'temp',
    'build',
    'dist'
)

foreach ($relativePath in $directories) {
    $path = Join-Path $RepoRoot $relativePath
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python was not found in PATH. Install a supported Python version first.'
}

$pythonVersion = & python --version
Write-Host "Detected: $pythonVersion"

if (-not (Test-Path $VenvPath)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
    & python -m venv $VenvPath
}

$venvPython = Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python was not created: $venvPython"
}

if (-not $SkipInstall) {
    Write-Host 'Installing project in editable mode...' -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e $RepoRoot
}

Write-Host ''
Write-Host 'Bootstrap complete.' -ForegroundColor Green
Write-Host "Run: $venvPython -m ai_sorter"
Write-Host "Or:  .\.venv\Scripts\ai-sorter.exe"
