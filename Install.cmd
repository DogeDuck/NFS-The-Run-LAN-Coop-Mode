@echo off
if not "%~1"=="" goto advanced
start "" "%SystemRoot%\System32\wscript.exe" "%~dp0Setup.vbs"
exit /b
:advanced
call "%~dp0PowerShell7.cmd" -NoProfile -File "%~dp0Install-Coop.ps1" %*
exit /b %errorlevel%
