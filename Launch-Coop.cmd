@echo off
call "%~dp0PowerShell7.cmd" -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0Connect-Coop.ps1" %*
if errorlevel 1 pause
