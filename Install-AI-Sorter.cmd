@echo off
setlocal
rem AI-Sorter installer bootstrap v2026.09.09.3
set "BOOTSTRAP_URL=https://raw.githubusercontent.com/macqo004/AI-sorter/feature/application-foundation/tools/install-one-shot.ps1"
echo AI-Sorter installer bootstrap v2026.09.09.3
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$p=Join-Path $env:TEMP 'AI-Sorter-bootstrap.ps1'; try { $u='%BOOTSTRAP_URL%?cachebust=' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); Write-Host ('Downloading bootstrap: ' + $u) -ForegroundColor DarkGray; Invoke-WebRequest -Uri $u -OutFile $p -UseBasicParsing; & $p } catch { Write-Host 'AI-Sorter installer could not be downloaded or started.' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }"
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
