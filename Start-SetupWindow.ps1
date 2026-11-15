# Windows PowerShell5.1: separate UI process avoids inheriting WScript SW_HIDE.
$ErrorActionPreference='Stop'
$info=New-Object Diagnostics.ProcessStartInfo
$info.FileName=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$info.Arguments='-STA -NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'Setup-Coop.ps1')+'"'
$info.WorkingDirectory=$PSScriptRoot;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
[void][Diagnostics.Process]::Start($info)
