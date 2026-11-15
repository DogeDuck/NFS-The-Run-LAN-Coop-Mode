@echo off
if not "%~1"=="" goto advanced
start "" "%SystemRoot%\System32\wscript.exe" "%~dp0Launch-Coop.vbs"
exit /b
:advanced
call "%~dp0PowerShell7.cmd" -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0Connect-Coop.ps1" %*
exit /b %errorlevel%
