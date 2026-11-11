#requires -Version 7.0
# Koop-Launcher: Host oder Beitreten, Name, Host-IP (wird gemerkt), Spielordner, Host-Optionen.
# Autoauswahl entfaellt hier: das Garage-Fenster oeffnet sich mit dem Spiel.
# Hintergrundbild (optional, nicht im Paket): %LOCALAPPDATA%\TheRunStoryCoop\launcher-background.jpg|png
param([switch]$CheckOnly,[switch]$ValidateForm,[switch]$CarChoiceOnly,[string]$Screenshot,[ValidateSet('auto','de','en')][string]$Language='auto',[string]$StateDirectory)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-Language.ps1')
. (Join-Path $PSScriptRoot 'Coop-MusicMix.ps1')
. (Join-Path $PSScriptRoot 'Coop-Graphics.ps1')
$stateRoot=if($StateDirectory){[IO.Path]::GetFullPath($StateDirectory)}else{Get-CoopPersonalStateRoot}
$script:CoopLanguage=Get-CoopLanguage $Language $stateRoot
$starter=Join-Path $PSScriptRoot 'Start-Coop.ps1'
if(!(Test-Path -LiteralPath $starter)){throw (Get-CoopText MissingStarter)}
$launcherFile=Join-Path $stateRoot 'launcher.json'



function Read-LauncherState{
    $s=[ordered]@{Role='Host';Nickname='CoopHost';HostIp='';GameDirectory='';MaxPlayers=2;Difficulty=1;AutoUpdate=$true;ShowServerWindow=$false;MusicMix=$true;MusicMixApplied=''}
    foreach($key in $script:CoopGraphicsKeys){$s[$key]=$script:CoopGraphicsDefaults[$key]}
    try{
        if(Test-Path -LiteralPath $launcherFile){
            $j=Get-Content -LiteralPath $launcherFile -Raw -Encoding utf8|ConvertFrom-Json
            if($j.Role -in @('Host','Guest','Solo')){$s.Role=[string]$j.Role}
            if($j.Nickname -match '^[A-Za-z0-9_-]{1,16}$'){$s.Nickname=[string]$j.Nickname}
            if($j.HostIp -is [string]){$s.HostIp=$j.HostIp}
            if($j.GameDirectory -is [string]){$s.GameDirectory=$j.GameDirectory}
            $limit=0
            if([int]::TryParse([string]$j.MaxPlayers,[ref]$limit) -and $limit -ge 1 -and $limit -le 4){$s.MaxPlayers=$limit}
            if($j.ShowServerWindow -is [bool]){$s.ShowServerWindow=$j.ShowServerWindow}
            if($j.PSObject.Properties.Name -contains 'Difficulty'){
                $level=0;if([int]::TryParse([string]$j.Difficulty,[ref]$level) -and $level -ge 0 -and $level -le 3){$s.Difficulty=$level}
            }
            if($j.AutoUpdate -is [bool]){$s.AutoUpdate=$j.AutoUpdate}
            if($j.MusicMix -is [bool]){$s.MusicMix=$j.MusicMix}
            if($j.MusicMixApplied -in @('Target','Original')){$s.MusicMixApplied=[string]$j.MusicMixApplied}
            $graphics=ConvertTo-CoopGraphicsSettings $j
            foreach($key in $script:CoopGraphicsKeys){$s[$key]=$graphics[$key]}
        }
        if(!$s.GameDirectory){$old=Join-Path $stateRoot 'settings.json';if(Test-Path -LiteralPath $old){$s.GameDirectory=(Get-Content -LiteralPath $old -Raw|ConvertFrom-Json).GameDirectory}}
    }catch{}
    return $s
}
function Save-LauncherState($s){
    if($null -ne $difficultyBox){$s['Difficulty']=[int]$difficultyBox.SelectedIndex}
    if($null -ne $autoUpdates){$s['AutoUpdate']=[bool]$autoUpdates.Checked}
    # Persoenlich: Musik-Mix an/aus und der zuletzt vom Launcher gesetzte Audiozustand.
    if($null -ne $musicMix){$s['MusicMix']=[bool]$musicMix.Checked}
    $s['MusicMixApplied']=[string]$script:MusicMixApplied
    # Persoenlich: Grafik-Werte fuer die Definitive-Edition-INI.
    if($null -ne $script:Graphics){foreach($key in $script:CoopGraphicsKeys){$s[$key]=[int]$script:Graphics[$key]}}
    if(!(Test-Path -LiteralPath $stateRoot)){[void](New-Item -ItemType Directory -Path $stateRoot)}
    $tmp=Join-Path $stateRoot ([IO.Path]::GetRandomFileName())
    try{
        [IO.File]::WriteAllText($tmp,($s|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
        [IO.File]::Move($tmp,$launcherFile,$true)
    }finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp}}
}
function Get-LauncherBackground{
    foreach($ext in '.jpg','.jpeg','.png','.bmp'){$p=Join-Path $stateRoot ('launcher-background'+$ext);if(Test-Path -LiteralPath $p){return $p}}
    return $null
}

$state=Read-LauncherState
# Maschinenlesbare Pruefausgaben (Tools/Tests) immer UTF-8, unabhaengig von der Konsolen-Codepage (z.B. cp850).
function Set-LauncherCheckOutputEncoding{if([Console]::IsOutputRedirected){try{[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)}catch{}}}
if($CheckOnly){Set-LauncherCheckOutputEncoding}
if($CheckOnly){[ordered]@{Status='configuration-check-only';Language=$script:CoopLanguage;Fields=@('Host','Guest','Solo','HostIp','Nickname','GameDirectory','MaxPlayers','Difficulty','AutoUpdate','ShowServerWindow','MusicMix','Graphics','Language');Preferences=$state;Port=25200;CarChoiceOnly=[bool]$CarChoiceOnly;DifficultyControlAvailable=$true;StartsGame=$false}|ConvertTo-Json -Depth 5;return}
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$script:Labels=@{}
$C=@{Text=[Drawing.Color]::FromArgb(240,240,240);Muted=[Drawing.Color]::FromArgb(185,185,190);Accent=[Drawing.Color]::FromArgb(235,125,30)
     Panel=[Drawing.Color]::FromArgb(235,14,14,17);Field=[Drawing.Color]::FromArgb(32,32,36);Edge=[Drawing.Color]::FromArgb(80,80,86)}
$font=New-Object Drawing.Font('Segoe UI',10)

$form=New-Object Windows.Forms.Form
$form.Text=Get-CoopText Title;$form.ClientSize=New-Object Drawing.Size(800,590)
$form.FormBorderStyle='FixedSingle';$form.MaximizeBox=$false;$form.StartPosition='CenterScreen';$form.Font=$font
$form.BackColor=[Drawing.Color]::FromArgb(18,18,22);$form.BackgroundImageLayout='Zoom'
$bgPath=Get-LauncherBackground
function Set-Background([string]$Path){
    $bytes=[IO.File]::ReadAllBytes($Path);$stream=[IO.MemoryStream]::new($bytes,$false)
    try{$source=[Drawing.Image]::FromStream($stream);try{$replacement=[Drawing.Bitmap]::new($source)}finally{$source.Dispose()}}finally{$stream.Dispose()}
    $old=$form.BackgroundImage;$form.BackgroundImage=$replacement;if($old){$old.Dispose()}
    $form.Invalidate()
}
if($bgPath){try{Set-Background $bgPath}catch{}}
$form.Add_Paint({param($s,$e)
    if(!$form.BackgroundImage){
        $r=$form.ClientRectangle
        $b=New-Object Drawing.Drawing2D.LinearGradientBrush($r,[Drawing.Color]::FromArgb(40,32,26),[Drawing.Color]::FromArgb(12,12,16),35)
        $e.Graphics.FillRectangle($b,$r);$b.Dispose()
    }
})

# Halbtransparente Karte rechts: alle Eingaben gut lesbar auf dunklem Grund.
$card=New-Object Windows.Forms.Panel;$card.Location=New-Object Drawing.Point(380,15);$card.Size=New-Object Drawing.Size(405,560);$card.BackColor=$C.Panel
$form.Controls.Add($card)
function New-Label([string]$Text,[int]$X,[int]$Y,[int]$W=340,$Color=$C.Muted,[float]$Size=9.5,[switch]$Bold){
    $l=New-Object Windows.Forms.Label;$l.Text=$Text;if($Text -and $script:CoopStrings.en.ContainsKey($Text)){$script:Labels[$Text]=$l;$l.Text=Get-CoopText $Text};$l.Location=New-Object Drawing.Point($X,$Y);$l.Size=New-Object Drawing.Size($W,22)
    $l.ForeColor=$Color;$l.BackColor=[Drawing.Color]::Transparent
    $l.Font=New-Object Drawing.Font('Segoe UI',$Size,$(if($Bold){[Drawing.FontStyle]::Bold}else{[Drawing.FontStyle]::Regular}))
    $card.Controls.Add($l);return $l
}
function New-Box([int]$X,[int]$Y,[int]$W){
    $b=New-Object Windows.Forms.TextBox;$b.Location=New-Object Drawing.Point($X,$Y);$b.Size=New-Object Drawing.Size($W,26)
    $b.BackColor=$C.Field;$b.ForeColor=$C.Text;$b.BorderStyle='FixedSingle';$card.Controls.Add($b);return $b
}
function New-FlatButton([string]$Text,[int]$X,[int]$Y,[int]$W,[int]$H=30){
    $b=New-Object Windows.Forms.Button;$b.Text=$Text;$b.Location=New-Object Drawing.Point($X,$Y);$b.Size=New-Object Drawing.Size($W,$H)
    $b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=$C.Edge;$b.BackColor=$C.Field;$b.ForeColor=$C.Text;$card.Controls.Add($b);return $b
}
function Set-On($b,[bool]$on){$b.BackColor=if($on){$C.Accent}else{$C.Field};$b.ForeColor=if($on){[Drawing.Color]::Black}else{$C.Text}}

[void](New-Label 'Story' 20 16 340 $C.Accent 9 -Bold)
[void](New-Label 'Need for Speed: The Run' 20 36 340 $C.Text 15 -Bold)
[void](New-Label 'Language' 20 72 190)
$languageBox=New-Object Windows.Forms.ComboBox;$languageBox.DropDownStyle='DropDownList';$languageBox.Location=New-Object Drawing.Point(230,69);$languageBox.Size=New-Object Drawing.Size(155,28)
$languageBox.BackColor=$C.Field;$languageBox.ForeColor=$C.Text;$languageBox.FlatStyle='Flat'
[void]$languageBox.Items.AddRange(@('Deutsch','English'));$card.Controls.Add($languageBox)
$languageBox.SelectedIndex=if($script:CoopLanguage -eq 'de'){0}else{1}
$btnHost=New-FlatButton '' 20 111 115 35
$btnJoin=New-FlatButton '' 145 111 115 35
$btnSolo=New-FlatButton '' 270 111 115 35
[void](New-Label 'Nickname' 20 157)
$nickname=New-Box 20 181 365
$lblIp=New-Label 'HostIp' 20 218
$ip=New-Box 20 242 365
[void](New-Label 'GameDirectory' 20 279)
$directory=New-Box 20 303 263
$browse=New-FlatButton '' 290 302 95 28
$lblOptions=New-Label 'HostOptions' 20 343 340 $C.Accent 8.5 -Bold
$lblMax=New-Label 'MaxPlayers' 20 370 110
$maxPlayers=New-Object Windows.Forms.NumericUpDown;$maxPlayers.Location=New-Object Drawing.Point(130,368);$maxPlayers.Size=New-Object Drawing.Size(56,26)
$maxPlayers.Minimum=1;$maxPlayers.Maximum=4;$maxPlayers.BackColor=$C.Field;$maxPlayers.ForeColor=$C.Text;$card.Controls.Add($maxPlayers)
$showServer=New-Object Windows.Forms.CheckBox;$showServer.Text='Serverfenster anzeigen';$showServer.Location=New-Object Drawing.Point(200,369);$showServer.Size=New-Object Drawing.Size(190,26)
$showServer.ForeColor=$C.Text;$showServer.BackColor=[Drawing.Color]::Transparent;$card.Controls.Add($showServer)
$hint=New-Label '' 20 443 365 $C.Muted 8.5;$hint.Size=New-Object Drawing.Size(365,58)
$start=New-FlatButton '' 20 510 270 35;$start.BackColor=$C.Accent;$start.ForeColor=[Drawing.Color]::Black;$start.Font=New-Object Drawing.Font('Segoe UI',10.5,[Drawing.FontStyle]::Bold)
$bgButton=New-FlatButton '' 300 510 85 35
$form.AcceptButton=$start
$difficulty=New-Label 'Difficulty' 20 407 110 $C.Muted 9
$difficultyBox=New-Object Windows.Forms.ComboBox
$difficultyBox.DropDownStyle='DropDownList';$difficultyBox.Location=New-Object Drawing.Point(130,404);$difficultyBox.Size=New-Object Drawing.Size(255,28)
$difficultyBox.BackColor=$C.Field;$difficultyBox.ForeColor=$C.Text;$difficultyBox.FlatStyle='Flat';$card.Controls.Add($difficultyBox)
[void]$difficultyBox.Items.AddRange(@('Easy','Normal','Hard','Extreme'));$difficultyBox.SelectedIndex=[int]$state.Difficulty

$nickname.Text=$state.Nickname;$ip.Text=[string]$state.HostIp;$directory.Text=[string]$state.GameDirectory
$maxPlayers.Value=[Math]::Min(4,[Math]::Max(1,[int]$state.MaxPlayers));$showServer.Checked=[bool]$state.ShowServerWindow
$script:Mode=if($state.Role -in @('Host','Guest','Solo')){$state.Role}else{'Host'}
$script:IsHost=($script:Mode -eq 'Host')
$script:AutomaticNickname=($state.Nickname -in @('CoopHost','CoopGuest',''))
# Musik-Mix: persoenlicher Schalter fuer alle Modi (Standard an), links ueber dem Update-Bereich.
$script:MusicMixApplied=[string]$state.MusicMixApplied
$musicMix=New-Object Windows.Forms.CheckBox;$musicMix.Location=New-Object Drawing.Point(20,412);$musicMix.Size=New-Object Drawing.Size(340,30)
$musicMix.ForeColor=$C.Text;$musicMix.BackColor=[Drawing.Color]::Transparent;$musicMix.Checked=[bool]$state.MusicMix;$form.Controls.Add($musicMix)
# Grafik: persoenliche DE-Werte (Standard = ausgeliefertes Profil), Fenster ueber dem Musik-Mix-Schalter.
$script:Graphics=ConvertTo-CoopGraphicsSettings $state
$graphicsButton=New-Object Windows.Forms.Button;$graphicsButton.Location=New-Object Drawing.Point(20,374);$graphicsButton.Size=New-Object Drawing.Size(340,32)
$graphicsButton.FlatStyle='Flat';$graphicsButton.FlatAppearance.BorderColor=$C.Edge;$graphicsButton.BackColor=$C.Field;$graphicsButton.ForeColor=$C.Text;$form.Controls.Add($graphicsButton)
function Get-GraphicsChoiceText([string]$Key,[int]$Value){
    switch($Key){
        'FPSLimit'{if($Value -lt 0){return Get-CoopText GraphicsUncapped};return [string]$Value}
        'ShadowmapResolution'{if($Value -lt 0){return Get-CoopText GraphicsGame};return [string]$Value}
        'ShadowmapViewDistance'{if($Value -eq 200){return '200 ('+(Get-CoopText GraphicsGame)+')'};return [string]$Value}
        'AnisotropicFiltering'{return [string]$Value+'x'}
        'ForceFov'{if($Value -le 0){return (Get-CoopText GraphicsGame)+' (48°)'};return [string]$Value+'°'}
    }
}
function Update-GraphicsButton{$graphicsButton.Text=Get-CoopText GraphicsButton -Values @((Get-GraphicsChoiceText 'FPSLimit' $script:Graphics.FPSLimit))}
# Baut das Grafik-Fenster (ohne es zu zeigen); Rueckgabe Fenster und Auswahlfelder.
function New-GraphicsDialog([int]$RefreshRate=0){
    $dialog=New-Object Windows.Forms.Form;$dialog.Text=Get-CoopText GraphicsTitle;$dialog.ClientSize=New-Object Drawing.Size(420,404)
    $dialog.FormBorderStyle='FixedDialog';$dialog.MaximizeBox=$false;$dialog.MinimizeBox=$false;$dialog.StartPosition='CenterParent'
    $dialog.BackColor=[Drawing.Color]::FromArgb(18,18,22);$dialog.ForeColor=$C.Text;$dialog.Font=$font
    $boxes=[ordered]@{};$y=16
    foreach($key in $script:CoopGraphicsKeys){
        $label=New-Object Windows.Forms.Label;$label.Text=Get-CoopText ('Graphics'+$key);$label.Location=New-Object Drawing.Point(16,($y+3));$label.Size=New-Object Drawing.Size(190,24);$label.ForeColor=$C.Muted
        $box=New-Object Windows.Forms.ComboBox;$box.DropDownStyle='DropDownList';$box.Location=New-Object Drawing.Point(210,$y);$box.Size=New-Object Drawing.Size(194,28)
        $box.BackColor=$C.Field;$box.ForeColor=$C.Text;$box.FlatStyle='Flat'
        foreach($choice in $script:CoopGraphicsChoices[$key]){[void]$box.Items.Add((Get-GraphicsChoiceText $key $choice))}
        $box.SelectedIndex=[Array]::IndexOf([int[]]$script:CoopGraphicsChoices[$key],[int]$script:Graphics[$key])
        $dialog.Controls.Add($label);$dialog.Controls.Add($box);$boxes[$key]=$box;$y+=38
    }
    $monitor=if($RefreshRate -gt 1){Get-CoopText GraphicsMonitor -Values @($RefreshRate)}else{''}
    $hintLabel=New-Object Windows.Forms.Label;$hintLabel.Text=Get-CoopText GraphicsHint -Values @($monitor);$hintLabel.Location=New-Object Drawing.Point(16,($y+2));$hintLabel.Size=New-Object Drawing.Size(390,58);$hintLabel.ForeColor=$C.Muted
    $dialog.Controls.Add($hintLabel)
    # Spiel-eigene Grafikoptionen (VSync, Aufloesung, Qualitaet) liegen im Spielstand: nur Hinweis, keine Aenderung.
    $vsyncLabel=New-Object Windows.Forms.Label;$vsyncLabel.Text=Get-CoopText GraphicsVsyncHint;$vsyncLabel.Location=New-Object Drawing.Point(16,($y+62));$vsyncLabel.Size=New-Object Drawing.Size(390,78);$vsyncLabel.ForeColor=$C.Accent
    $dialog.Controls.Add($vsyncLabel)
    $defaults=New-Object Windows.Forms.Button;$defaults.Text=Get-CoopText GraphicsDefaults;$defaults.Location=New-Object Drawing.Point(16,360);$defaults.Size=New-Object Drawing.Size(120,32);$defaults.FlatStyle='Flat';$defaults.BackColor=$C.Field
    $defaults.Add_Click({foreach($key in $script:CoopGraphicsKeys){$boxes[$key].SelectedIndex=[Array]::IndexOf([int[]]$script:CoopGraphicsChoices[$key],[int]$script:CoopGraphicsDefaults[$key])}}.GetNewClosure())
    $ok=New-Object Windows.Forms.Button;$ok.Text='OK';$ok.DialogResult='OK';$ok.Location=New-Object Drawing.Point(198,360);$ok.Size=New-Object Drawing.Size(100,32);$ok.FlatStyle='Flat';$ok.BackColor=$C.Accent;$ok.ForeColor=[Drawing.Color]::Black
    $cancel=New-Object Windows.Forms.Button;$cancel.Text=Get-CoopText GraphicsCancel;$cancel.DialogResult='Cancel';$cancel.Location=New-Object Drawing.Point(304,360);$cancel.Size=New-Object Drawing.Size(100,32);$cancel.FlatStyle='Flat';$cancel.BackColor=$C.Field
    $dialog.Controls.AddRange(@($defaults,$ok,$cancel));$dialog.AcceptButton=$ok;$dialog.CancelButton=$cancel
    return [pscustomobject]@{Form=$dialog;Boxes=$boxes;Hint=$hintLabel;VsyncHint=$vsyncLabel}
}
$graphicsButton.Add_Click({
    $built=New-GraphicsDialog (Get-CoopMonitorRefreshRate)
    try{
        if($built.Form.ShowDialog($form) -eq 'OK'){
            $chosen=[ordered]@{};foreach($key in $script:CoopGraphicsKeys){$chosen[$key]=$script:CoopGraphicsChoices[$key][$built.Boxes[$key].SelectedIndex]}
            $script:Graphics=ConvertTo-CoopGraphicsSettings $chosen;Update-GraphicsButton
        }
    }finally{$built.Form.Dispose()}
})
$script:UpdatingNickname=$false
$nickname.Add_TextChanged({if(!$script:UpdatingNickname){$script:AutomaticNickname=$false}})

function Update-Role{
    $script:IsHost=($script:Mode -eq 'Host');$solo=($script:Mode -eq 'Solo')
    Set-On $btnHost ($script:Mode -eq 'Host');Set-On $btnJoin ($script:Mode -eq 'Guest');Set-On $btnSolo $solo
    $ip.Enabled=($script:Mode -eq 'Guest');$lblIp.Enabled=$ip.Enabled
    foreach($c in $lblOptions,$lblMax,$maxPlayers,$showServer,$difficulty,$difficultyBox){$c.Visible=$script:IsHost}
    $nickname.Enabled=!$solo
    if(!$solo -and $script:AutomaticNickname){
        $script:UpdatingNickname=$true
        try{$nickname.Text=if($script:IsHost){'CoopHost'}else{'CoopGuest'}}finally{$script:UpdatingNickname=$false}
    }
    $start.Text=Get-CoopText $(if($solo){'StartSolo'}elseif($script:IsHost){'StartHost'}else{'StartGuest'})
    $hint.Text=Get-CoopText $(if($solo){'SoloHint'}elseif($script:IsHost){'HostHint'}else{'GuestHint'})
    $difficulty.Text=Get-CoopText Difficulty
}
function Update-Language {
    $form.Text=Get-CoopText Title
    foreach($key in $script:Labels.Keys){$script:Labels[$key].Text=Get-CoopText $key}
    $btnHost.Text=Get-CoopText Host;$btnJoin.Text=Get-CoopText Guest;$btnSolo.Text=Get-CoopText Solo
    $browse.Text=Get-CoopText Browse;$showServer.Text=Get-CoopText ShowServer;$bgButton.Text=Get-CoopText Background;$musicMix.Text=Get-CoopText MusicMix;Update-GraphicsButton
    $selectedDifficulty=$difficultyBox.SelectedIndex
    $difficultyBox.Items.Clear()
    [void]$difficultyBox.Items.AddRange(@((Get-CoopText DifficultyEasy),(Get-CoopText DifficultyNormal),(Get-CoopText DifficultyHard),(Get-CoopText DifficultyExtreme)))
    $difficultyBox.SelectedIndex=$selectedDifficulty
    if($null -ne $autoUpdates){$autoUpdates.Text=Get-CoopText AutoUpdates;$updateButton.Text=Get-CoopText CheckUpdates}
    Update-Role
}
$languageBox.Add_SelectedIndexChanged({
    $script:CoopLanguage=if($languageBox.SelectedIndex -eq 0){'de'}else{'en'}
    Update-Language
    try{Save-CoopLanguage $script:CoopLanguage $stateRoot}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,(Get-CoopText Title))}
})
$btnHost.Add_Click({$script:Mode='Host';Update-Role})
$btnJoin.Add_Click({$script:Mode='Guest';Update-Role})
$btnSolo.Add_Click({$script:Mode='Solo';Update-Role})
$browse.Add_Click({
    $dialog=New-Object Windows.Forms.OpenFileDialog
    try{$dialog.Title=Get-CoopText ChooseExe;$dialog.Filter=Get-CoopText ExeFilter;if($dialog.ShowDialog() -eq 'OK'){$directory.Text=[IO.Path]::GetDirectoryName($dialog.FileName)}}finally{$dialog.Dispose()}
})
$bgButton.Add_Click({
    $dialog=New-Object Windows.Forms.OpenFileDialog
    try{
        $dialog.Title=Get-CoopText ChooseBackground;$dialog.Filter=Get-CoopText ImageFilter
        if($dialog.ShowDialog() -eq 'OK'){
            # Decode before replacing previous local files; release all file handles.
            Set-Background $dialog.FileName
            if(!(Test-Path -LiteralPath $stateRoot)){[void](New-Item -ItemType Directory -Path $stateRoot)}
            $target=Join-Path $stateRoot ('launcher-background'+[IO.Path]::GetExtension($dialog.FileName).ToLowerInvariant())
            if([IO.Path]::GetFullPath($dialog.FileName) -ne [IO.Path]::GetFullPath($target)){Copy-Item -LiteralPath $dialog.FileName -Destination $target -Force}
            foreach($old in Get-ChildItem -LiteralPath $stateRoot -Filter 'launcher-background.*' -File){if($old.FullName -ne $target){Remove-Item -LiteralPath $old.FullName}}
        }
    }catch{[Windows.Forms.MessageBox]::Show($_.Exception.Message,(Get-CoopText BackgroundTitle))|Out-Null}finally{$dialog.Dispose()}
})
Update-Language

# Updates run in a hidden worker; slow/offline GitHub never blocks the form.
$updatePanel=New-Object Windows.Forms.Panel
$updatePanel.Location=New-Object Drawing.Point(15,446);$updatePanel.Size=New-Object Drawing.Size(345,138)
$updatePanel.BackColor=[Drawing.Color]::Transparent;$form.Controls.Add($updatePanel)
$autoUpdates=New-Object Windows.Forms.CheckBox
$autoUpdates.Location=New-Object Drawing.Point(5,70);$autoUpdates.Size=New-Object Drawing.Size(335,32)
$autoUpdates.ForeColor=$C.Text;$autoUpdates.BackColor=[Drawing.Color]::Transparent;$autoUpdates.Checked=[bool]$state.AutoUpdate
$autoUpdates.Text=Get-CoopText AutoUpdates;$updatePanel.Controls.Add($autoUpdates)
$updateButton=New-Object Windows.Forms.Button
$updateButton.Location=New-Object Drawing.Point(5,106);$updateButton.Size=New-Object Drawing.Size(335,31)
$updateButton.FlatStyle='Flat';$updateButton.BackColor=$C.Field;$updateButton.ForeColor=$C.Text;$updateButton.Text=Get-CoopText CheckUpdates
$updatePanel.Controls.Add($updateButton)
$updateStatus=New-Object Windows.Forms.Label
$updateStatus.Location=New-Object Drawing.Point(5,0);$updateStatus.Size=New-Object Drawing.Size(335,62)
$updateStatus.ForeColor=$C.Muted;$updateStatus.BackColor=[Drawing.Color]::Transparent;$updatePanel.Controls.Add($updateStatus)
try{$packageVersion=[string](Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package-manifest.json') -Raw -Encoding utf8|ConvertFrom-Json).version}catch{$packageVersion='Development'}
$updateStatus.Text='v'+$packageVersion
$script:UpdateProcess=$null;$script:UpdateResult=$null;$script:UpdateInstalling=$false
function Start-LauncherUpdate([switch]$Install){
    if($script:UpdateProcess -and !$script:UpdateProcess.HasExited){return}
    $worker=Join-Path $PSScriptRoot 'Update-Coop.ps1'
    if(!(Test-Path -LiteralPath $worker)){$updateStatus.Text=Get-CoopText UpdateOffline;return}
    if($Install){
        if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){$updateStatus.Text=Get-CoopText UpdateGameRunning;return}
        if(!$directory.Text.Trim()){$updateStatus.Text=Get-CoopText UpdateChooseGame;return}
    }
    $script:UpdateResult=Join-Path $stateRoot ('Updates\result-'+[Guid]::NewGuid().ToString('N')+'.json')
    $info=[Diagnostics.ProcessStartInfo]::new((Join-Path $PSHOME 'pwsh.exe'))
    $info.UseShellExecute=$false;$info.CreateNoWindow=$true
    $mode=if($Install){'-Install'}else{'-CheckOnly'}
    foreach($arg in @('-NoProfile','-File',$worker,$mode,'-CurrentPackageDirectory',$PSScriptRoot,'-ResultPath',$script:UpdateResult)){$info.ArgumentList.Add($arg)}
    if($Install){$info.ArgumentList.Add('-GameDirectory');$info.ArgumentList.Add($directory.Text.Trim().Trim('"'))}
    $script:UpdateInstalling=[bool]$Install
    $updateStatus.Text=Get-CoopText $(if($Install){'UpdateInstalling'}else{'UpdateChecking'})
    $updateButton.Enabled=$false;if($Install){$start.Enabled=$false}
    $script:UpdateProcess=[Diagnostics.Process]::Start($info)
}
$updateTimer=New-Object Windows.Forms.Timer;$updateTimer.Interval=400
$updateTimer.Add_Tick({
    if(!$script:UpdateProcess){return}
    if(!(Test-Path -LiteralPath $script:UpdateResult)){
        if($script:UpdateProcess.HasExited){$updateStatus.Text=Get-CoopText UpdateOffline;$updateButton.Enabled=$true;$start.Enabled=$true;$script:UpdateProcess=$null}
        return
    }
    try{
        $result=Get-Content -LiteralPath $script:UpdateResult -Raw -Encoding utf8|ConvertFrom-Json
        $script:UpdateProcess=$null;$updateButton.Enabled=$true;$start.Enabled=$true
        switch($result.Status){
            'current' {$updateStatus.Text=Get-CoopText UpdateCurrent}
            'available' {
                $updateStatus.Text=Get-CoopText UpdateAvailable -Values @($result.Version)
                if($autoUpdates.Checked){Start-LauncherUpdate -Install}
            }
            'game-running' {$updateStatus.Text=Get-CoopText UpdateGameRunning}
            'missing-game' {$updateStatus.Text=Get-CoopText UpdateChooseGame}
            'installed' {
                $newPackage=[IO.Path]::GetFullPath([string]$result.PackageDirectory)
                $gamePrefix=[IO.Path]::GetFullPath($directory.Text.Trim().Trim('"')).TrimEnd('\')+'\'
                if(!$newPackage.StartsWith($gamePrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Updated package is outside the game folder.'}
                Save-CoopLanguage $script:CoopLanguage $stateRoot
                Save-LauncherState ([ordered]@{Role=$script:Mode;Nickname=$nickname.Text;HostIp=$ip.Text;GameDirectory=$directory.Text;MaxPlayers=[int]$maxPlayers.Value;ShowServerWindow=$showServer.Checked})
                $info=[Diagnostics.ProcessStartInfo]::new((Join-Path $PSHOME 'pwsh.exe'));$info.UseShellExecute=$false;$info.CreateNoWindow=$true
                foreach($arg in @('-NoProfile','-File',(Join-Path $newPackage 'Connect-Coop.ps1'),'-Language',$script:CoopLanguage)){$info.ArgumentList.Add($arg)}
                [void][Diagnostics.Process]::Start($info);$form.Close()
            }
            'failed' {$updateStatus.Text=Get-CoopText UpdateFailed -Values @([string]$result.Error)}
            default {$updateStatus.Text=Get-CoopText UpdateOffline}
        }
    }catch{$updateStatus.Text=Get-CoopText UpdateFailed -Values @($_.Exception.Message);$updateButton.Enabled=$true;$start.Enabled=$true;$script:UpdateProcess=$null}
})
$updateButton.Add_Click({Start-LauncherUpdate -Install})
$form.Add_Shown({if(!$CarChoiceOnly -and !$ValidateForm){$updateTimer.Start();Start-LauncherUpdate}})
$form.Add_FormClosed({$updateTimer.Stop();$updateTimer.Dispose()})

function Quote-CoopLiteral([string]$Value){return "'"+$Value.Replace("'","''")+"'"}
# Vor jedem Start (Spiel ist geschlossen): Musik-Mix passend setzen. Fehler blockieren den Start nicht.
function Invoke-LauncherMusicMix([string]$Game){
    $form.UseWaitCursor=$true
    try{$script:MusicMixApplied=(Invoke-CoopMusicMix $Game ([bool]$musicMix.Checked) ([string]$script:MusicMixApplied)).State}
    catch{[void][Windows.Forms.MessageBox]::Show((Get-CoopText MusicMixFailed -Values @($_.Exception.Message)),(Get-CoopText Title))}
    finally{$form.UseWaitCursor=$false}
}
# Vor jedem Start: persoenliche Grafikwerte in die DE-INI. Fehler blockieren den Start nicht.
function Invoke-LauncherGraphics([string]$Game){
    try{[void](Set-CoopGraphicsIni $Game $script:Graphics)}
    catch{[void][Windows.Forms.MessageBox]::Show((Get-CoopText GraphicsFailed -Values @($_.Exception.Message)),(Get-CoopText Title))}
}
$form.Add_FormClosing({
    if($ValidateForm -or $CarChoiceOnly){return}
    try{
        Save-CoopLanguage $script:CoopLanguage $stateRoot
        Save-LauncherState ([ordered]@{Role=$script:Mode;Nickname=$nickname.Text;HostIp=$ip.Text.Trim();GameDirectory=$directory.Text.Trim().Trim('"');MaxPlayers=[int]$maxPlayers.Value;ShowServerWindow=$showServer.Checked})
    }catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,(Get-CoopText Title))}
})
$start.Add_Click({
    try{
        if($CarChoiceOnly){[Windows.Forms.MessageBox]::Show((Get-CoopText GarageHint),(Get-CoopText GarageTitle))|Out-Null;$form.Close();return}
        if(!$directory.Text.Trim()){throw (Get-CoopText MissingGame)}
        $game=[IO.Path]::GetFullPath($directory.Text.Trim().Trim('"'))
        if(!(Test-Path -LiteralPath (Join-Path $game 'Need For Speed The Run.exe'))){throw (Get-CoopText MissingGame)}
        if($script:Mode -eq 'Solo'){
            # Einzelspieler mit allen Mods (DE, Musik, Debug-Menue); nur LAN-Tweaks fuer die Sitzung aus.
            if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw (Get-CoopText Running)}
            Invoke-LauncherMusicMix $game
            Invoke-LauncherGraphics $game
            Save-CoopLanguage $script:CoopLanguage $stateRoot
            Save-LauncherState ([ordered]@{Role='Solo';Nickname=$nickname.Text;HostIp=$ip.Text.Trim();GameDirectory=$game;MaxPlayers=[int]$maxPlayers.Value;ShowServerWindow=$showServer.Checked})
            $solo=Join-Path $PSScriptRoot 'Start-Solo.ps1'
            $info=New-Object Diagnostics.ProcessStartInfo
            $info.FileName=Join-Path $PSHOME 'pwsh.exe';$info.UseShellExecute=$false;$info.CreateNoWindow=$true
            foreach($argument in @('-NoProfile','-ExecutionPolicy','Bypass','-File',$solo,'-GameDirectory',$game,'-Language',$script:CoopLanguage,'-ShowErrorDialog')){[void]$info.ArgumentList.Add($argument)}
            [void][Diagnostics.Process]::Start($info)
            $form.Close();return
        }
        if($nickname.Text -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw (Get-CoopText BadNickname)}
        if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw (Get-CoopText Running)}
        $role=if($script:IsHost){'Host'}else{'Guest'}
        $address=if($script:IsHost){'127.0.0.1'}else{$ip.Text.Trim()}
        $parsed=$null
        if(![Net.IPAddress]::TryParse($address,[ref]$parsed) -or $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw (Get-CoopText BadIp)}
        Invoke-LauncherMusicMix $game
        Invoke-LauncherGraphics $game
        Save-CoopLanguage $script:CoopLanguage $stateRoot
        Save-LauncherState ([ordered]@{Role=$role;Nickname=$nickname.Text;HostIp=$ip.Text.Trim();GameDirectory=$game;MaxPlayers=[int]$maxPlayers.Value;ShowServerWindow=$showServer.Checked})
        $command='& {0} -Role {1} -GameDirectory {2} -HostAddress {3} -Nickname {4} -MaxPlayers {5} -Language {6}' -f (Quote-CoopLiteral $starter),(Quote-CoopLiteral $role),(Quote-CoopLiteral $game),(Quote-CoopLiteral $address),(Quote-CoopLiteral $nickname.Text),[int]$maxPlayers.Value,(Quote-CoopLiteral $script:CoopLanguage)
        if($script:IsHost){$command+=' -Difficulty '+[int]$difficultyBox.SelectedIndex}
        if($script:IsHost -and $showServer.Checked){$command+=' -ShowServerWindow'}
        $command='try { '+$command+' } catch { Write-Host $_.Exception.Message; Read-Host '+(Quote-CoopLiteral (Get-CoopText StartFailed))+' | Out-Null; exit 1 }'
        $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
        # Konsole bleibt sichtbar: der Host bestaetigt dort, wenn der Gast bereit ist.
        Start-Process -FilePath (Join-Path $PSHOME 'pwsh.exe') -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) | Out-Null
        $form.Close()
    }catch{[Windows.Forms.MessageBox]::Show((ConvertTo-CoopUserError $_.Exception.Message),(Get-CoopText ConnectionTitle))|Out-Null}
})
try{
    if($ValidateForm){
        Set-LauncherCheckOutputEncoding
        $languageStates=[ordered]@{};$originalLanguage=$script:CoopLanguage
        foreach($languageCode in 'de','en'){
            $script:CoopLanguage=$languageCode;Update-Language
            $languageStates[$languageCode]=[ordered]@{Title=$form.Text;Host=$btnHost.Text;Guest=$btnJoin.Text;Solo=$btnSolo.Text;Nickname=$script:Labels.Nickname.Text;GameDirectory=$script:Labels.GameDirectory.Text;ShowServer=$showServer.Text;MusicMix=$musicMix.Text;Graphics=$graphicsButton.Text;GraphicsTitle=(Get-CoopText GraphicsTitle)}
        }
        $script:CoopLanguage=$originalLanguage;Update-Language
        $roleStates=[ordered]@{};$originalMode=$script:Mode
        foreach($role in 'Host','Guest','Solo'){
            $script:Mode=$role;Update-Role
            $roleStates[$role]=[ordered]@{StartText=$start.Text;IpEnabled=$ip.Enabled;NicknameEnabled=$nickname.Enabled;HostOptionsAvailable=$script:IsHost;Hint=$hint.Text;Difficulty=$difficulty.Text}
        }
        $script:Mode=$originalMode;Update-Role
        [ordered]@{Status='form-constructed';Language=$script:CoopLanguage;SelectedLanguage=$languageBox.Text;LanguageStates=$languageStates;Controls=$card.Controls.Count;HostSelected=$script:IsHost;Background=[bool]$form.BackgroundImage;Roles=$roleStates;DifficultyIndex=$difficultyBox.SelectedIndex;DifficultyOptions=@($difficultyBox.Items);AutoUpdate=$autoUpdates.Checked;MusicMix=$musicMix.Checked;Graphics=$script:Graphics;GraphicsDialog=$(try{$probe=New-GraphicsDialog 144;[ordered]@{Boxes=$probe.Boxes.Count;Selected=[ordered]@{FPSLimit=$probe.Boxes.FPSLimit.Text;ForceFov=$probe.Boxes.ForceFov.Text};Hint=$probe.Hint.Text;VsyncHint=$probe.VsyncHint.Text}}finally{if($probe){$probe.Form.Dispose()}});UpdateWorkerStarted=($null -ne $script:UpdateProcess);StartsGame=$false}|ConvertTo-Json -Depth 5
        if($Screenshot){
            # An unshown Form hides all descendants. Render the detached child panel
            # separately: it has no top-level window and never takes focus.
            $bmp=New-Object Drawing.Bitmap($form.Width,$form.Height)
            $panelBitmap=New-Object Drawing.Bitmap($card.Width,$card.Height)
            try{
                $form.DrawToBitmap($bmp,(New-Object Drawing.Rectangle(0,0,$form.Width,$form.Height)))
                $border=[int](($form.Width-$form.ClientSize.Width)/2)
                $top=$form.Height-$form.ClientSize.Height-$border
                $form.Controls.Remove($card)
                $card.DrawToBitmap($panelBitmap,(New-Object Drawing.Rectangle(0,0,$card.Width,$card.Height)))
                # Native ComboBox omits its selected text in DrawToBitmap on this
                # Windows build. Draw the actual control value into the preview.
                $panelGraphics=[Drawing.Graphics]::FromImage($panelBitmap)
                try{
                    foreach($combo in $languageBox,$difficultyBox){
                        $fieldBrush=[Drawing.SolidBrush]::new($combo.BackColor);$textBrush=[Drawing.SolidBrush]::new($combo.ForeColor)
                        try{
                            $panelGraphics.FillRectangle($fieldBrush,$combo.Left+2,$combo.Top+2,$combo.Width-21,$combo.Height-4)
                            $panelGraphics.DrawString($combo.Text,$combo.Font,$textBrush,$combo.Left+5,$combo.Top+3)
                        }finally{$textBrush.Dispose();$fieldBrush.Dispose()}
                    }
                }finally{$panelGraphics.Dispose()}
                $graphics=[Drawing.Graphics]::FromImage($bmp)
                $updateBitmap=New-Object Drawing.Bitmap($updatePanel.Width,$updatePanel.Height)
                try{
                    $graphics.DrawImageUnscaled($panelBitmap,$card.Left+$border,$card.Top+$top)
                    $form.Controls.Remove($updatePanel)
                    $updatePanel.DrawToBitmap($updateBitmap,(New-Object Drawing.Rectangle(0,0,$updatePanel.Width,$updatePanel.Height)))
                    $graphics.DrawImageUnscaled($updateBitmap,$updatePanel.Left+$border,$updatePanel.Top+$top)
                }finally{$form.Controls.Add($updatePanel);$updateBitmap.Dispose();$graphics.Dispose()}
                $bmp.Save([IO.Path]::GetFullPath($Screenshot),[Drawing.Imaging.ImageFormat]::Png)
            }finally{$form.Controls.Add($card);$panelBitmap.Dispose();$bmp.Dispose()}
        }
    }else{$form.ShowDialog()|Out-Null}
}finally{if($form.BackgroundImage){$form.BackgroundImage.Dispose()};$form.Dispose()}
