@echo off
setlocal
set "BOOTSTRAP_URL=https://raw.githubusercontent.com/macqo004/AI-sorter/feature/application-foundation/tools/install-one-shot.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$p=Join-Path $env:TEMP 'AI-Sorter-bootstrap.ps1'; Invoke-WebRequest -Uri '%BOOTSTRAP_URL%' -OutFile $p -UseBasicParsing; & $p"
exit /b %errorlevel%
