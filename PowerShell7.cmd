@echo off
where pwsh.exe >nul 2>&1
if errorlevel 1 goto standard
pwsh.exe %*
exit /b %errorlevel%
:standard
if not exist "%ProgramFiles%\PowerShell\7\pwsh.exe" goto missing
"%ProgramFiles%\PowerShell\7\pwsh.exe" %*
exit /b %errorlevel%
:missing
echo PowerShell 7 fehlt. Bitte PowerShell 7 installieren und erneut starten.
exit /b 1
