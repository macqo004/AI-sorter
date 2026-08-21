@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install-one-shot.ps1" %*
exit /b %errorlevel%
