#requires -Version 7.0
param([ValidateSet('auto','de','en')][string]$Language='auto',[switch]$SelfTest,[string]$StateDirectory)
. (Join-Path $PSScriptRoot 'Coop-Language.ps1')
. (Join-Path $PSScriptRoot 'Coop-UserData.ps1')
$script:CoopLanguage=Get-CoopLanguage $Language
$de=$script:CoopLanguage -eq 'de'
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$form=[Windows.Forms.Form]::new();$form.Text=if($de){'Koop-Sitzung'}else{'Co-op session'};$form.ClientSize='620,360';$form.StartPosition='CenterScreen';$form.BackColor=[Drawing.Color]::FromArgb(24,24,27);$form.ForeColor=[Drawing.Color]::White
$text=[Windows.Forms.TextBox]::new();$text.Multiline=$true;$text.ReadOnly=$true;$text.ScrollBars='Vertical';$text.Dock='Fill';$text.Font=[Drawing.Font]::new('Segoe UI',11);$text.BackColor=$form.BackColor;$text.ForeColor=$form.ForeColor;$form.Controls.Add($text)
$state=if($StateDirectory){$StateDirectory}else{Get-CoopPersonalStateRoot}
function Format-SessionRole([string]$Role){if($de -and $Role -eq 'Guest'){return 'Gast'};if($de -and $Role -eq 'Solo'){return 'Einzelspieler'};return $Role}
function Format-SessionFlag([bool]$Value){if($de){if($Value){return 'Ja'};return 'Nein'};if($Value){return 'Yes'};return 'No'}
function Format-SessionPeerStatus([string]$Value){
 $labels=@{waiting=@('Wartet','Waiting');compatible=@('Passende Version','Matching version');unavailable=@('Nicht erreichbar','Unavailable');'port-unavailable'=@('Sitzungsport belegt','Session port unavailable');full=@('Sitzung voll','Session full');mismatch=@('Andere Modversion','Different mod version');'duplicate-name'=@('Spielername bereits belegt','Nickname already in use');solo=@('Einzelspieler','Single player')}
 if($labels.ContainsKey($Value)){return $labels[$Value][$(if($de){0}else{1})]};return $Value
}
function Update-SessionOverview{
 try{
  $session=Read-CoopJsonObject (Join-Path $state 'active-session.json')
  if(!$session.SessionDirectory){throw 'none'}
  $row=Read-CoopJsonObject (Join-Path $session.SessionDirectory 'session-status.json')
  if(!$row.Count){throw 'none'}
  $lines=@(('Version: '+$row.Version),($(if($de){'Dein Spieler: '}else{'Your player: '})+$row.Nickname+' ('+(Format-SessionRole $row.Role)+')'),($(if($de){'Spiel aktiv: '}else{'Game active: '})+(Format-SessionFlag $row.Active)),'',($(if($de){'Launcher-Verbindungen (kein Renn-Ranking):'}else{'Launcher connections (not race standings):'})))
  foreach($p in $row.Players){$lines+= '  '+$p.Nickname+' · '+(Format-SessionRole $p.Role)+' · '+$p.Version}
  $lines+= ''; $lines+= ($(if($de){'Verbindungsprüfung: '}else{'Connection check: '})+(Format-SessionPeerStatus $row.PeerStatus))
  $lines+= ($(if($de){'Diagnose: '}else{'Diagnostics: '})+(Format-SessionFlag $row.DiagnosticsEnabled))
  if($row.DiagnosticDirectory){$lines+=$row.DiagnosticDirectory}
  if($null -ne $row.ExitCode){$lines+= ($(if($de){'Spiel-Endcode: '}else{'Game exit code: '})+[string]$row.ExitCode)}
  $text.Text=$lines -join "`r`n"
 }catch{$text.Text=if($de){'Noch keine Sitzung. Starte Host, Beitreten oder Einzelspieler über den Launcher.'}else{'No session yet. Start Host, Join or Single player from the launcher.'}}
}
Update-SessionOverview
if($SelfTest){[ordered]@{Title=$form.Text;Text=$text.Text;StartsGame=$false;WritesGame=$false}|ConvertTo-Json;$form.Dispose();return}
$timer=[Windows.Forms.Timer]::new();$timer.Interval=2000;$timer.Add_Tick({Update-SessionOverview});$form.Add_Shown({$timer.Start()});$form.Add_FormClosed({$timer.Stop();$timer.Dispose()});[void]$form.ShowDialog();$form.Dispose()
