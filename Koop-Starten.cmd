@echo off
powershell.exe -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0Connect-Coop.ps1"
if errorlevel 1 pause
