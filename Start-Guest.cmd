@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Coop.ps1" -Role Guest %*
pause
