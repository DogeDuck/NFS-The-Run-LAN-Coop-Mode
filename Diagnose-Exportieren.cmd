@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Diagnostics.ps1" -Action Export %*
pause
