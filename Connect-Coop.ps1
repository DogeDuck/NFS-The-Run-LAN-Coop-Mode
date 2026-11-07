#requires -Version 7.0
param([switch]$CheckOnly,[switch]$ValidateForm,[switch]$CarChoiceOnly)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Car-Choice.ps1')
. (Join-Path $PSScriptRoot 'Car-Preferences.ps1')
$startCars=@(Get-CoopStartCars)
$starter=Join-Path $PSScriptRoot 'Start-Coop.ps1'
if(!(Test-Path -LiteralPath $starter)){throw 'Start-Coop.ps1 fehlt im Paket.'}
if($CheckOnly){[ordered]@{Status='configuration-check-only';Fields=@('Host oder Beitreten','Radmin-IP des Hosts','Spielername','Spielordner','Gespeichertes Auto');StartCars=@($startCars|Select-Object Id,Name);Port=25200;CarChoiceOnly=[bool]$CarChoiceOnly;StartsGame=$false}|ConvertTo-Json;return}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$form=New-Object Windows.Forms.Form
$form.Text='NFS The Run – Koop verbinden'
if($CarChoiceOnly){$form.Text='NFS The Run – Autoauswahl speichern'}
$form.ClientSize=New-Object Drawing.Size(570,400)
$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false;$form.StartPosition='CenterScreen'
$hostOption=New-Object Windows.Forms.RadioButton
$hostOption.Text='Spiel hosten';$hostOption.Location=New-Object Drawing.Point(20,18);$hostOption.Size=New-Object Drawing.Size(160,25);$hostOption.Checked=$true
$guestOption=New-Object Windows.Forms.RadioButton
$guestOption.Text='Spiel beitreten';$guestOption.Location=New-Object Drawing.Point(210,18);$guestOption.Size=New-Object Drawing.Size(170,25)
$form.Controls.AddRange(@($hostOption,$guestOption))
function Add-Field([string]$Caption,[int]$Y,[int]$Width=365){
 $label=New-Object Windows.Forms.Label;$label.Text=$Caption;$label.Location=New-Object Drawing.Point(20,($Y+3));$label.Size=New-Object Drawing.Size(160,23)
 $box=New-Object Windows.Forms.TextBox;$box.Location=New-Object Drawing.Point(185,$Y);$box.Size=New-Object Drawing.Size($Width,25)
 $form.Controls.AddRange(@($label,$box));return $box
}
$ip=Add-Field 'Radmin-IP des Hosts' 65
$nickname=Add-Field 'Spielername' 105;$nickname.Text='CoopHost'
$directory=Add-Field 'Spielordner' 145 265
$settings=Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\settings.json'
if(Test-Path -LiteralPath $settings){try{$directory.Text=(Get-Content -LiteralPath $settings -Raw|ConvertFrom-Json).GameDirectory}catch{}}
$browse=New-Object Windows.Forms.Button;$browse.Text='Auswählen';$browse.Location=New-Object Drawing.Point(458,143);$browse.Size=New-Object Drawing.Size(92,28)
$browse.Add_Click({
 $dialog=New-Object Windows.Forms.OpenFileDialog
 try{$dialog.Title='Need For Speed The Run.exe auswählen';$dialog.Filter='Spiel-EXE|Need For Speed The Run.exe';if($dialog.ShowDialog() -eq 'OK'){$directory.Text=[IO.Path]::GetDirectoryName($dialog.FileName)}}finally{$dialog.Dispose()}
})
$carLabel=New-Object Windows.Forms.Label;$carLabel.Text='Gespeichertes Auto';$carLabel.Location=New-Object Drawing.Point(20,188);$carLabel.Size=New-Object Drawing.Size(160,25)
$carChoice=New-Object Windows.Forms.ComboBox;$carChoice.Location=New-Object Drawing.Point(185,185);$carChoice.Size=New-Object Drawing.Size(365,25);$carChoice.DropDownStyle='DropDownList'
foreach($car in $startCars){[void]$carChoice.Items.Add($car.Name)};$carChoice.SelectedIndex=0
$form.Controls.AddRange(@($carLabel,$carChoice))
$hint=New-Object Windows.Forms.Label;$hint.Location=New-Object Drawing.Point(20,230);$hint.Size=New-Object Drawing.Size(530,105)
$hint.Text='Jeder Spieler waehlt sein eigenes Auto. Die Auswahl wird je Rolle und Spielername gespeichert und beim naechsten Koop-Start wieder geladen. Vor dem Rennen einmal VIEW CARS / AUTOS ANSEHEN oeffnen. Die Auswahl bleibt in der Sitzung erzwungen; gescriptete Story-Autos koennen abweichen. Tankstellen weiterhin meiden.'
$start=New-Object Windows.Forms.Button;$start.Text='Als Host starten';$start.Location=New-Object Drawing.Point(345,350);$start.Size=New-Object Drawing.Size(205,34)
$form.Controls.AddRange(@($browse,$hint,$start));$form.AcceptButton=$start
function Restore-CoopCarSelection {
 if($nickname.Text -notmatch '^[A-Za-z0-9_-]{1,16}$'){return}
 $role=if($hostOption.Checked){'Host'}else{'Guest'}
 $saved=Get-CoopSavedStartCar $role $nickname.Text
 for($i=0;$i -lt $startCars.Count;$i++){if($startCars[$i].Id -ieq $saved){$carChoice.SelectedIndex=$i;break}}
}
$hostOption.Add_CheckedChanged({
 $ip.Enabled=$guestOption.Checked -and !$CarChoiceOnly
 $start.Text=if($CarChoiceOnly){'Autoauswahl speichern'}elseif($hostOption.Checked){'Als Host starten'}else{'Verbinden'}
 if($nickname.Text -in @('CoopHost','CoopGuest')){$nickname.Text=if($hostOption.Checked){'CoopHost'}else{'CoopGuest'}}
 Restore-CoopCarSelection
})
$nickname.Add_TextChanged({Restore-CoopCarSelection})
$lastProfile=Get-CoopLastCarProfile
$nickname.Text=$lastProfile.Nickname
$guestOption.Checked=$lastProfile.Role -eq 'Guest'
Restore-CoopCarSelection
$ip.Enabled=$guestOption.Checked -and !$CarChoiceOnly
if($guestOption.Checked -and !$CarChoiceOnly){$start.Text='Verbinden'}
if($CarChoiceOnly){$directory.Enabled=$false;$browse.Enabled=$false;$start.Text='Autoauswahl speichern';$hint.Text='Auto fuer Rolle und Spielername waehlen und speichern. Wirksam beim naechsten Koop-Start. Das Spiel wird hier nicht gestartet und der Spielstand bleibt unberuehrt. Danach im Hauptmenue einmal VIEW CARS oeffnen. Gescriptete Story-Autos koennen abweichen.'}
function Quote-CoopLiteral([string]$Value){return "'"+$Value.Replace("'","''")+"'"}
$start.Add_Click({
 try{
  if($CarChoiceOnly){
   $role=if($hostOption.Checked){'Host'}else{'Guest'}
   Save-CoopCarPreference $role $nickname.Text $startCars[$carChoice.SelectedIndex].Id
   [Windows.Forms.MessageBox]::Show('Autoauswahl gespeichert. Gilt beim naechsten Koop-Start.','Autoauswahl')|Out-Null
   $form.Close();return
  }
  $game=[IO.Path]::GetFullPath($directory.Text.Trim('"'))
  if(!(Test-Path -LiteralPath (Join-Path $game 'Need For Speed The Run.exe'))){throw 'Bitte den Spielordner mit der Spiel-EXE auswählen.'}
  if($nickname.Text -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw 'Spielername: 1–16 Buchstaben/Ziffern, _ oder -.'}
  $role=if($hostOption.Checked){'Host'}else{'Guest'}
  $address=if($hostOption.Checked){'127.0.0.1'}else{$ip.Text.Trim()}
  $parsed=$null
  if(![Net.IPAddress]::TryParse($address,[ref]$parsed) -or $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'Bitte eine gültige Radmin-IPv4 eintragen, ohne Port.'}
  $command='& {0} -Role {1} -GameDirectory {2} -HostAddress {3} -Nickname {4} -StartCarId {5}' -f (Quote-CoopLiteral $starter),(Quote-CoopLiteral $role),(Quote-CoopLiteral $game),(Quote-CoopLiteral $address),(Quote-CoopLiteral $nickname.Text),(Quote-CoopLiteral $startCars[$carChoice.SelectedIndex].Id)
  $command+='; if(-not $?) { Read-Host ''Starter fehlgeschlagen. Enter zum Schliessen'' | Out-Null }'
  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
  # Console is intentionally visible: the host must confirm when the guest is ready.
  Start-Process -FilePath (Join-Path $PSHOME 'pwsh.exe') -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) | Out-Null
  $form.Close()
 }catch{[Windows.Forms.MessageBox]::Show($_.Exception.Message,'Koop-Verbindung')|Out-Null}
})
try{
 if($ValidateForm){
  [ordered]@{Status='form-constructed';Controls=$form.Controls.Count;HostSelected=$hostOption.Checked;StartsGame=$false}|ConvertTo-Json
 }else{$form.ShowDialog()|Out-Null}
}finally{$form.Dispose()}
