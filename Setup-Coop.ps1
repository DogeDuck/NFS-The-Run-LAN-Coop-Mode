# Windows PowerShell5.1 GUI: runtime7 is prepared by the hidden installation worker.
param([ValidateSet('auto','de','en')][string]$Language='auto',[switch]$ValidateForm,[string]$Screenshot)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$script:CoopLanguage=$Language
if($Language -eq 'auto'){
 $script:CoopLanguage=if([Globalization.CultureInfo]::CurrentUICulture.Name -like 'de*'){'de'}else{'en'}
 try{$savedLanguage=Get-Content -LiteralPath (Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\language.json') -Raw -Encoding UTF8|ConvertFrom-Json;if($savedLanguage.Language -in @('de','en')){$script:CoopLanguage=[string]$savedLanguage.Language}}catch{}
}
$words=@{
 de=@{Title='The Run Co-op – Installation';Heading='Bereit für euren gemeinsamen Run';Intro='Installiert oder aktualisiert die Koop-Mod. Deine Einstellungen und Spielstände bleiben erhalten.';Game='Spielordner';Browse='Durchsuchen…';Lan='Geprüfte LAN-Basis herunterladen (ca.16MB)';Import='LAN-Archiv auswählen…';Folder='LAN-Ordner auswählen…';Imported='Optionaler Import';Credit='LAN Script: Hypercycle, And799, mRally2 · Originaldownload über MEGA';Shortcut='Desktop-Verknüpfung erstellen';Install='Installieren / aktualisieren';Close='Schließen';Ready='Spielordner wählen und Installation starten.';Checking='Dateien und Voraussetzungen werden geprüft…';Runtime='PowerShell7 wird geprüft / bei Bedarf vorbereitet…';Downloading='Originales LAN-Paket wird heruntergeladen und geprüft…';Importing='LAN-Dateien werden entpackt und geprüft…';Backup='Aktueller Spielstand wird gesichert…';Installing='Koop-Mod wird installiert…';Done='Installation abgeschlossen. Du kannst den Launcher öffnen.';Launch='Launcher öffnen';Failed='Installation nicht abgeschlossen. Einzelheiten stehen unten.';Needs='Passende LAN-Dateien fehlen. Automatischen Download aktivieren oder Archiv/Ordner auswählen.';Busy='Die Installation läuft. Bitte bis zum Abschluss warten.';Details='Einzelheiten';NeedGame='Bitte den Ordner mit Need For Speed The Run.exe wählen.';NotStarted='Vorschau: keine Installation gestartet.'}
 en=@{Title='The Run Co-op – Setup';Heading='Get ready for a shared run';Intro='Install or update the co-op mod. Your settings and saves are preserved.';Game='Game folder';Browse='Browse…';Lan='Download verified original LAN base (about16MB)';Import='Choose LAN archive…';Folder='Choose LAN folder…';Imported='Optional import';Credit='LAN Script: Hypercycle, And799, mRally2 · Original download via MEGA';Shortcut='Create desktop shortcut';Install='Install / update';Close='Close';Ready='Choose your game folder and start the installation.';Checking='Checking files and requirements…';Runtime='Checking PowerShell7 / preparing it if needed…';Downloading='Downloading and verifying the original LAN package…';Importing='Extracting and checking LAN files…';Backup='Backing up your current save…';Installing='Installing the co-op mod…';Done='Installation complete. You can open the launcher.';Launch='Open launcher';Failed='Installation did not complete. See the details below.';Needs='Matching LAN files are missing. Enable automatic download or select an archive/folder.';Busy='Installation is running. Please wait until it finishes.';Details='Details';NeedGame='Choose the folder containing Need For Speed The Run.exe.';NotStarted='Preview: no installation started.'}
}
function T([string]$key){return $words[$script:CoopLanguage][$key]}
$form=[Windows.Forms.Form]::new();$form.Text=T Title;$form.ClientSize=[Drawing.Size]::new(720,650)
$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false;$form.StartPosition='CenterScreen'
$form.Font=[Drawing.Font]::new('Segoe UI',10);$form.BackColor=[Drawing.Color]::FromArgb(20,20,24);$form.ForeColor=[Drawing.Color]::FromArgb(238,238,240)
function Label([string]$text,[int]$x,[int]$y,[int]$w,[int]$h){$c=[Windows.Forms.Label]::new();$c.Text=$text;$c.Location=[Drawing.Point]::new($x,$y);$c.Size=[Drawing.Size]::new($w,$h);$form.Controls.Add($c);return $c}
function Button([int]$x,[int]$y,[int]$w){$c=[Windows.Forms.Button]::new();$c.Location=[Drawing.Point]::new($x,$y);$c.Size=[Drawing.Size]::new($w,34);$c.FlatStyle='Flat';$c.BackColor=[Drawing.Color]::FromArgb(35,35,40);$form.Controls.Add($c);return $c}
$heading=Label '' 26 28 530 38;$heading.Font=[Drawing.Font]::new('Segoe UI Semibold',19)
$intro=Label '' 28 78 650 48
$languageBox=[Windows.Forms.ComboBox]::new();$languageBox.DropDownStyle='DropDownList';$languageBox.Items.AddRange(@('Deutsch','English'));$languageBox.Location='564,30';$languageBox.Size='128,25';$form.Controls.Add($languageBox)
$gameLabel=Label '' 28 141 620 24
$game=[Windows.Forms.TextBox]::new();$game.Location='28,171';$game.Size='518,26';$game.BackColor=[Drawing.Color]::FromArgb(34,34,39);$game.ForeColor=$form.ForeColor;$form.Controls.Add($game)
$browse=Button 560 167 132
$download=[Windows.Forms.CheckBox]::new();$download.Location='28,222';$download.Size='660,28';$download.Checked=$true;$form.Controls.Add($download)
$credit=Label '' 48 253 644 24;$credit.ForeColor=[Drawing.Color]::FromArgb(160,164,173)
$archive=Button 28 294 220;$folder=Button 258 294 220
$source=Label '' 28 339 664 36;$script:LanSource=''
$shortcut=[Windows.Forms.CheckBox]::new();$shortcut.Location='28,381';$shortcut.Size='650,28';$shortcut.Checked=$true;$form.Controls.Add($shortcut)
$status=Label '' 28 428 664 42;$status.ForeColor=[Drawing.Color]::FromArgb(239,151,61)
$bar=[Windows.Forms.ProgressBar]::new();$bar.Location='28,476';$bar.Size='664,8';$form.Controls.Add($bar)
$details=[Windows.Forms.TextBox]::new();$details.Location='28,499';$details.Size='664,76';$details.Multiline=$true;$details.ReadOnly=$true;$details.ScrollBars='Vertical';$details.BackColor=$game.BackColor;$details.ForeColor=$form.ForeColor;$form.Controls.Add($details)
$install=Button 28 596 318;$install.BackColor=[Drawing.Color]::FromArgb(235,125,30);$install.ForeColor=[Drawing.Color]::Black
$launch=Button 358 596 198;$launch.Enabled=$false;$close=Button 566 596 126
$script:Worker=$null;$script:ResultFile='';$script:InstalledPackage='';$script:Stage='';$script:Busy=$false
function Refresh-SetupLanguage {
 $form.Text=T Title;$heading.Text=T Heading;$intro.Text=T Intro;$gameLabel.Text=T Game;$browse.Text=T Browse;$download.Text=T Lan;$credit.Text=T Credit;$archive.Text=T Import;$folder.Text=T Folder;$shortcut.Text=T Shortcut;$install.Text=T Install;$launch.Text=T Launch;$close.Text=T Close
 if(!$script:Busy){$status.Text=T Ready}
 $source.Text=$(if($script:LanSource){(T Imported)+': '+$script:LanSource}else{''})
}
function Set-SetupBusy([bool]$value){$script:Busy=$value;foreach($c in @($install,$browse,$archive,$folder,$download,$shortcut,$languageBox,$game)){$c.Enabled=!$value};$bar.Style=$(if($value){'Marquee'}else{'Blocks'})}
$languageBox.Add_SelectedIndexChanged({$script:CoopLanguage=if($languageBox.SelectedIndex -eq 0){'de'}else{'en'};Refresh-SetupLanguage})
$languageBox.SelectedIndex=$(if($script:CoopLanguage -eq 'de'){0}else{1})
$browse.Add_Click({$dialog=[Windows.Forms.FolderBrowserDialog]::new();try{if($dialog.ShowDialog($form) -eq 'OK'){$game.Text=$dialog.SelectedPath}}finally{$dialog.Dispose()}})
$archive.Add_Click({$dialog=[Windows.Forms.OpenFileDialog]::new();$dialog.Filter='LAN archive|*.7z;*.zip';try{if($dialog.ShowDialog($form) -eq 'OK'){$script:LanSource=$dialog.FileName;Refresh-SetupLanguage}}finally{$dialog.Dispose()}})
$folder.Add_Click({$dialog=[Windows.Forms.FolderBrowserDialog]::new();try{if($dialog.ShowDialog($form) -eq 'OK'){$script:LanSource=$dialog.SelectedPath;Refresh-SetupLanguage}}finally{$dialog.Dispose()}})
$close.Add_Click({$form.Close()})
$launch.Add_Click({if($script:InstalledPackage){$info=[Diagnostics.ProcessStartInfo]::new();$info.FileName=Join-Path $env:WINDIR 'System32\wscript.exe';$info.Arguments='"'+(Join-Path $script:InstalledPackage 'Launch-Coop.vbs')+'"';$info.UseShellExecute=$false;$info.CreateNoWindow=$true;[void][Diagnostics.Process]::Start($info);$form.Close()}})
$install.Add_Click({
 try{
  $path=$game.Text.Trim().Trim('"')
  if(!(Test-Path -LiteralPath (Join-Path $path 'Need For Speed The Run.exe') -PathType Leaf)){throw (T NeedGame)}
  $script:Stage=Join-Path $env:LOCALAPPDATA ('TheRunStoryCoop\SetupSessions\'+[Guid]::NewGuid().ToString('N'));[void][IO.Directory]::CreateDirectory($script:Stage)
  $script:ResultFile=Join-Path $script:Stage 'result.json';$requestPath=Join-Path $script:Stage 'request.json'
  @{GameDirectory=$path;Language=$script:CoopLanguage;LanSource=$script:LanSource;DownloadLan=[bool]$download.Checked;DesktopShortcut=[bool]$shortcut.Checked;ResultPath=$script:ResultFile}|ConvertTo-Json|Set-Content -LiteralPath $requestPath -Encoding UTF8
  $info=[Diagnostics.ProcessStartInfo]::new();$info.FileName=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
  $info.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'Setup-CoopWorker.ps1')+'" -RequestPath "'+$requestPath+'"'
  $info.UseShellExecute=$false;$info.CreateNoWindow=$true
  Set-SetupBusy $true;$status.Text=T Runtime;$details.Text='';$launch.Enabled=$false
  $script:Worker=[Diagnostics.Process]::Start($info)
 }catch{Set-SetupBusy $false;$status.Text=T Failed;$details.Text=$_.Exception.Message}
})
$timer=[Windows.Forms.Timer]::new();$timer.Interval=300
$timer.Add_Tick({
 if(!$script:Worker){return}
 if(Test-Path -LiteralPath $script:ResultFile){
  try{$r=Get-Content -LiteralPath $script:ResultFile -Raw -Encoding UTF8|ConvertFrom-Json}catch{return}
  if($r.Status -eq 'working'){
   if($script:Worker.HasExited){Set-SetupBusy $false;$status.Text=T Failed;$details.Text=$script:Stage;$script:Worker.Dispose();$script:Worker=$null;return}
   $status.Text=T $(switch($r.Phase){'checking'{'Checking'};'downloading'{'Downloading'};'importing'{'Importing'};'backup'{'Backup'};'installing'{'Installing'};default{'Runtime'}});return
  }
  if(!$script:Worker.HasExited){return}
  Set-SetupBusy $false;$script:Worker.Dispose();$script:Worker=$null
  switch($r.Status){
   'installed'{$status.Text=T Done;$details.Text='v'+$r.Version+[Environment]::NewLine+$r.PackageDirectory+[Environment]::NewLine+$r.BackupDirectory;$script:InstalledPackage=[string]$r.PackageDirectory;$launch.Enabled=$true}
   'needs-lan'{$status.Text=T Needs;$details.Text=$r.Files -join [Environment]::NewLine}
   default{$status.Text=T Failed;$details.Text=[string]$r.Error}
  }
 }elseif($script:Worker.HasExited){Set-SetupBusy $false;$status.Text=T Failed;$details.Text=$script:Stage;$script:Worker.Dispose();$script:Worker=$null}
})
$form.Add_FormClosing({param($sender,$eventArgs)if($script:Busy){$eventArgs.Cancel=$true;[void][Windows.Forms.MessageBox]::Show((T Busy),$form.Text)}})
try{foreach($name in @('launcher.json','settings.json')){$path=Join-Path $env:LOCALAPPDATA ('TheRunStoryCoop\'+$name);if(Test-Path -LiteralPath $path){$saved=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json;if($saved.GameDirectory){$game.Text=[string]$saved.GameDirectory;break}}}}catch{}
Refresh-SetupLanguage
try{
 if($ValidateForm){
  $status.Text=T NotStarted
  if($Screenshot){$form.ShowInTaskbar=$false;$form.StartPosition='Manual';$form.Location=[Drawing.Point]::new(-20000,-20000);$form.Show();[Windows.Forms.Application]::DoEvents();$bitmap=[Drawing.Bitmap]::new($form.Width,$form.Height);try{$form.DrawToBitmap($bitmap,[Drawing.Rectangle]::new(0,0,$form.Width,$form.Height));$bitmap.Save([IO.Path]::GetFullPath($Screenshot))}finally{$bitmap.Dispose();$form.Hide()}}
  @{Language=$script:CoopLanguage;Controls=$form.Controls.Count;DownloadLan=$download.Checked;StartsWorker=$false;Title=$form.Text}|ConvertTo-Json -Compress
 }else{$timer.Start();[void]$form.ShowDialog()}
}finally{$timer.Stop();$timer.Dispose();$form.Dispose()}
