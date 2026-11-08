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
echo PowerShell 7 is missing. Install PowerShell 7, then try again.
echo PowerShell 7 fehlt. Bitte PowerShell 7 installieren und erneut starten.
echo https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows
exit /b 1
