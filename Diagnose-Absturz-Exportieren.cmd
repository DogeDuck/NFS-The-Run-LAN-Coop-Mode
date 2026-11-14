@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-CrashDiagnostics.ps1" -Action Export %*
pause
