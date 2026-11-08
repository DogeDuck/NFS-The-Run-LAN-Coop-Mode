#requires -Version 7.0
param([int]$GamePid=0,[switch]$RelayOnly,[switch]$PassThru,[ValidateSet('auto','de','en')][string]$Language='auto')
$ErrorActionPreference='Stop'
$garage=Join-Path $PSScriptRoot 'Garage-Fenster.ps1'
if(!(Test-Path -LiteralPath $garage -PathType Leaf)){throw 'Garage-Fenster.ps1 is missing / fehlt.'}
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName=Join-Path $PSHOME 'pwsh.exe'
$info.WorkingDirectory=$PSScriptRoot
$info.UseShellExecute=$false
# CREATE_NO_WINDOW suppresses only the console. SW_HIDE / WindowStyle Hidden
# also affects the first GUI window and can hide the WinForms garage itself.
$info.CreateNoWindow=$true
foreach($argument in @('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',$garage)){
    $info.ArgumentList.Add($argument)
}
if($GamePid -gt 0){$info.ArgumentList.Add('-GamePid');$info.ArgumentList.Add([string]$GamePid)}
if($RelayOnly){$info.ArgumentList.Add('-RelayOnly')}
if($Language -ne 'auto'){$info.ArgumentList.Add('-Language');$info.ArgumentList.Add($Language)}
$garageProcess=[Diagnostics.Process]::Start($info)
if($PassThru){return $garageProcess}
