# Windows PowerShell5.1 bootstrap. Capture forwarded arguments before dot-sourcing.
$launchArguments=@($args)
$ErrorActionPreference='Stop'
try{
 . (Join-Path $PSScriptRoot 'Coop-PowerShellRuntime.ps1')
 $runtime=Resolve-CoopPowerShell7
 & $runtime @launchArguments
 exit $LASTEXITCODE
}catch{
 $message='Launcher setup failed / Launcher-Vorbereitung fehlgeschlagen: '+$_.Exception.Message
 if(($launchArguments -join ' ') -match 'Start-(Coop|Garage)Window.ps1'){
  Add-Type -AssemblyName System.Windows.Forms
  [void][Windows.Forms.MessageBox]::Show($message,'The Run Co-op / Koop')
 }
 Write-Error $message
 exit 1
}
