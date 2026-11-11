#requires -Version 7.0
param([switch]$PassThru)
$ErrorActionPreference='Stop'
$launcher=Join-Path $PSScriptRoot 'Connect-Coop.ps1'
if(!(Test-Path -LiteralPath $launcher -PathType Leaf)){throw 'Connect-Coop.ps1 is missing / fehlt.'}
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName=Join-Path $PSHOME 'pwsh.exe'
$info.WorkingDirectory=$PSScriptRoot
$info.UseShellExecute=$false
# Do not inherit the VBS bootstrap's SW_HIDE for the first WinForms window.
# CREATE_NO_WINDOW suppresses only the console of this separate UI process.
$info.CreateNoWindow=$true
foreach($argument in @('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',$launcher)){
    $info.ArgumentList.Add($argument)
}
$launcherProcess=[Diagnostics.Process]::Start($info)
if($PassThru){return $launcherProcess}
