@echo off
call "%~dp0PowerShell7.cmd" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Coop.ps1" -Role Guest
if errorlevel 1 pause
