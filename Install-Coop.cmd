@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Coop.ps1" %*
pause
