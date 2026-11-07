#requires -Version 7.0
# Koop-Garage: Auto, Style-Pack und Variante fuer das EIGENE laufende Spiel waehlen.
# Wirkung beim naechsten Fahrzeug-Spawn (naechstes Rennen / Retry). -SelfTest baut nur das Fenster.
param([switch]$SelfTest,[string]$Screenshot,[int]$GamePid=0,[switch]$RelayOnly)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Garage-Core.ps1')
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()

$catalog=Get-GarageCatalog
foreach($car in $catalog.Cars){$label=if($car.Category -eq 'fun'){'★ Spaß · '+$car.Name}elseif($car.Tier){'Tier '+$car.Tier+' · '+$car.Name}else{$car.Name};$car|Add-Member -NotePropertyName Label -NotePropertyValue $label -Force}
$state=[ordered]@{Car=$null;Pack=$null;Variant=$null;GamePid=$GamePid;Slot=$null;HostIp=$null;LocalServer=$null;Listener=$null;Desired=@{};Current='';Fetching=@{}}
$C=@{Bg=[Drawing.Color]::FromArgb(24,24,27);Panel=[Drawing.Color]::FromArgb(36,36,40);Text=[Drawing.Color]::FromArgb(235,235,235)
     Muted=[Drawing.Color]::FromArgb(150,150,155);Accent=[Drawing.Color]::FromArgb(230,120,30);Ok=[Drawing.Color]::FromArgb(90,190,110);Bad=[Drawing.Color]::FromArgb(230,90,80)}
$font=New-Object Drawing.Font('Segoe UI',10)

function New-Btn([string]$Text,[int]$W=110){
    $b=New-Object Windows.Forms.Button
    $b.Text=$Text;$b.Width=$W;$b.Height=32;$b.FlatStyle='Flat';$b.ForeColor=$C.Text;$b.BackColor=$C.Panel
    $b.FlatAppearance.BorderColor=[Drawing.Color]::FromArgb(70,70,75);$b.Margin='3,3,3,3';$b.Font=$font
    return $b
}
function Set-On($b,[bool]$on){$b.BackColor=if($on){$C.Accent}else{$C.Panel};$b.ForeColor=if($on){[Drawing.Color]::Black}else{$C.Text}}

$form=New-Object Windows.Forms.Form
$form.Text='The Run Koop – Garage';$form.Size='980,720';$form.MinimumSize='860,640';$form.BackColor=$C.Bg;$form.ForeColor=$C.Text;$form.Font=$font;$form.StartPosition='CenterScreen'

# Kopfzeile: wer bin ich, wo ist der Server (alles automatisch)
$top=New-Object Windows.Forms.TableLayoutPanel;$top.Dock='Top';$top.Height=58;$top.Padding='12,6,12,6';$top.BackColor=$C.Panel;$top.ColumnCount=1;$top.RowCount=2
$lblWho=New-Object Windows.Forms.Label;$lblWho.AutoSize=$true;$lblWho.Font=New-Object Drawing.Font('Segoe UI',11,[Drawing.FontStyle]::Bold);$lblWho.Text='Suche dein Spiel ...'
$lblStatus=New-Object Windows.Forms.Label;$lblStatus.AutoSize=$true;$lblStatus.ForeColor=$C.Muted
$top.Controls.Add($lblWho,0,0);$top.Controls.Add($lblStatus,0,1)

# Links: Suche + Liste
$left=New-Object Windows.Forms.Panel;$left.Dock='Left';$left.Width=270;$left.Padding='8,8,4,8'
$txtSearch=New-Object Windows.Forms.TextBox;$txtSearch.Dock='Top';$txtSearch.PlaceholderText='Auto suchen';$txtSearch.BackColor=$C.Panel;$txtSearch.ForeColor=$C.Text;$txtSearch.BorderStyle='FixedSingle'
$lst=New-Object Windows.Forms.ListBox;$lst.Dock='Fill';$lst.BackColor=$C.Panel;$lst.ForeColor=$C.Text;$lst.BorderStyle='None';$lst.IntegralHeight=$false;$lst.ItemHeight=22
$left.Controls.Add($lst);$left.Controls.Add($txtSearch)

# Rechts: Vorschau + Auswahl
$right=New-Object Windows.Forms.FlowLayoutPanel;$right.Dock='Fill';$right.FlowDirection='TopDown';$right.WrapContents=$false;$right.Padding='12,8,8,8';$right.AutoScroll=$true
$pic=New-Object Windows.Forms.PictureBox;$pic.Size='620,260';$pic.SizeMode='Zoom';$pic.BackColor=$C.Panel
$lblName=New-Object Windows.Forms.Label;$lblName.AutoSize=$true;$lblName.Font=New-Object Drawing.Font('Segoe UI',13,[Drawing.FontStyle]::Bold);$lblName.Margin='3,8,3,2'
$lblPreview=New-Object Windows.Forms.Label;$lblPreview.AutoSize=$true;$lblPreview.ForeColor=$C.Muted
$lblSource=New-Object Windows.Forms.Label;$lblSource.AutoSize=$true;$lblSource.MaximumSize='620,0';$lblSource.ForeColor=$C.Accent
$lblPack=New-Object Windows.Forms.Label;$lblPack.Text='Paket';$lblPack.AutoSize=$true;$lblPack.ForeColor=$C.Muted;$lblPack.Margin='3,10,3,0'
$packs=New-Object Windows.Forms.FlowLayoutPanel;$packs.AutoSize=$true;$packs.WrapContents=$true;$packs.MaximumSize='620,0'
$lblVar=New-Object Windows.Forms.Label;$lblVar.Text='Variante / Lack';$lblVar.AutoSize=$true;$lblVar.ForeColor=$C.Muted;$lblVar.Margin='3,8,3,0'
$vars=New-Object Windows.Forms.FlowLayoutPanel;$vars.AutoSize=$true;$vars.WrapContents=$true;$vars.MaximumSize='620,0'
$actions=New-Object Windows.Forms.FlowLayoutPanel;$actions.AutoSize=$true;$actions.Margin='0,14,0,0'
$btnApply=New-Btn 'Fürs nächste Rennen übernehmen' 290;$btnApply.BackColor=$C.Accent;$btnApply.ForeColor=[Drawing.Color]::Black
$btnStory=New-Btn 'Story-Auto' 110
$btnImage=New-Btn 'Vorschaubild...' 130
$btnShot=New-Btn 'Foto aus Spiel' 130
$actions.Controls.AddRange(@($btnApply,$btnStory,$btnShot,$btnImage))
$lblKey=New-Object Windows.Forms.Label;$lblKey.AutoSize=$true;$lblKey.ForeColor=$C.Muted;$lblKey.Margin='3,6,3,3'
$lblHint=New-Object Windows.Forms.Label;$lblHint.AutoSize=$true;$lblHint.MaximumSize='620,0';$lblHint.ForeColor=$C.Muted
$lblHint.Text='Du wählst nur dein eigenes Auto. Es kommt beim nächsten Etappenstart und bleibt auch nach Retry, solange dieses Fenster offen ist. Der Host muss sein Garage-Fenster ebenfalls offen haben.'
$right.Controls.AddRange(@($pic,$lblName,$lblSource,$lblPreview,$lblPack,$packs,$lblVar,$vars,$actions,$lblKey,$lblHint))

$form.Controls.Add($right);$form.Controls.Add($left);$form.Controls.Add($top)

function Set-Status([string]$Text,$Color){$lblStatus.Text=$Text;$lblStatus.ForeColor=$Color}

function Show-Preview{
    $v=$state.Variant
    if($pic.Image){$old=$pic.Image;$pic.Image=$null;$old.Dispose()}
    $path=if($v){Get-GaragePreviewPath $v.DatabaseEntry $state.Car.Id}else{$null}
    if($path){
        $bytes=[IO.File]::ReadAllBytes($path);$ms=New-Object IO.MemoryStream(,$bytes)
        $pic.Image=[Drawing.Image]::FromStream($ms);$lblPreview.Text=(Get-GaragePreviewCredit $path)
    }else{
        $car=$state.Car
        if($car -and !$state.Fetching.ContainsKey($car.Id) -and (Start-GaragePhotoDownload $car {if($state.Car -eq $car){Show-Preview}}.GetNewClosure())){
            $state.Fetching[$car.Id]=$true;$lblPreview.Text='Lade Foto von Wikimedia Commons ...'
        }elseif($state.Fetching.ContainsKey($car.Id)){$lblPreview.Text='Kein Foto gefunden – "Foto aus Spiel" oder eigenes Bild hineinziehen.'}
        else{$lblPreview.Text='Kein Vorschaubild – "Foto aus Spiel" klicken oder ein Bild ins Fenster ziehen.'}
    }
}

function Show-Variants{
    $vars.Controls.Clear()
    foreach($v in $state.Pack.Variants){
        $b=New-Btn ([string]$v.N) 44;$b.Tag=$v
        Set-On $b ($v -eq $state.Variant)
        $b.Add_Click({param($s,$e)$state.Variant=$s.Tag;Show-Variants;Show-Preview})
        $vars.Controls.Add($b)
    }
    $lblKey.Text=if($state.Variant){'Kennung: {0}  (0x{1:X8})' -f $state.Variant.DatabaseEntry,[uint32]$state.Variant.VehicleKey}else{''}
}

function Show-Packs{
    $packs.Controls.Clear()
    foreach($p in $state.Car.Packs){
        $b=New-Btn $p.Label 120;$b.Tag=$p
        Set-On $b ($p -eq $state.Pack)
        $b.Add_Click({param($s,$e)$state.Pack=$s.Tag;$state.Variant=$s.Tag.Variants[0];Show-Packs;Show-Variants;Show-Preview})
        $packs.Controls.Add($b)
    }
}

function Select-Car($car,[string]$PackId,[int]$N){
    $state.Car=$car
    $state.Pack=@($car.Packs|Where-Object Pack -eq $PackId)[0]; if(!$state.Pack){$state.Pack=$car.Packs[0]}
    $state.Variant=@($state.Pack.Variants|Where-Object N -eq $N)[0]; if(!$state.Variant){$state.Variant=$state.Pack.Variants[0]}
    $lblName.Text=$car.Name
    $lblSource.Text=if($car.Category -eq 'fun'){'Spaß (experimentell, nicht offiziell fahrbar) – Liste aus: '+$car.Source}elseif($car.Tier){'Tier '+$car.Tier+' von 6 (Serienversion laut NFS-Wiki)'}else{''}
    Show-Packs;Show-Variants;Show-Preview
}

function Fill-List{
    $q=$txtSearch.Text.Trim()
    $lst.BeginUpdate();$lst.Items.Clear()
    foreach($car in $catalog.Cars){if(!$q -or $car.Name -like "*$q*"){[void]$lst.Items.Add($car)}}
    $lst.DisplayMember='Label';$lst.EndUpdate()
    if($state.Car -and $lst.Items.Contains($state.Car)){$lst.SelectedItem=$state.Car}
}

function Get-OwnGame{
    if($state.GamePid){$p=Get-Process -Id $state.GamePid -ErrorAction SilentlyContinue;if($p -and $p.ProcessName -eq 'Need For Speed The Run'){return $p};return $null}
    $all=@(Get-GarageGameProcesses);if($all.Count -eq 1){$state.GamePid=$all[0].Id;return $all[0]}
    return $null
}

function Update-Identity{
    # Laeuft im Hintergrund: eigenes Spiel, eigene Spieler-Nummer, Server lokal oder beim Host.
    $g=Get-OwnGame
    if(!$g -and $state.GamePid){$form.Close();return}   # auch nach manuellem Oeffnen ans eigene Spiel binden
    if(!$g){$lblWho.Text='Warte auf dein Spiel ...';$state.Slot=$null;return}
    if($state.HostIp -eq $null){$state.HostIp=Get-GarageClientServerIp $g.Id}
    $slot=Get-GarageClientPlayerId $g.Id
    $state.Slot=$slot
    # A local guest must use the same host relay as a guest on another PC.
    $sp=if(!$RelayOnly){@(Get-GarageServerProcesses)[0]}else{$null}
    if($sp -and !$state.LocalServer){try{$state.LocalServer=$sp.Id;$state.Listener=Start-GarageRelayListener}catch{Set-Status ('Gast-Anfragen nicht moeglich: '+$_.Exception.Message) $C.Bad}}
    if(!$sp -and $state.LocalServer){$state.LocalServer=$null;if($state.Listener){$state.Listener.Stop();$state.Listener=$null}}
    $role=if($state.LocalServer){'Host'}else{'Gast'}
    if($slot -eq $null){$lblWho.Text=('Dein Auto ({0}) – warte, bis du im Rennen bist ...' -f $role);return}
    $cur=''
    if($state.LocalServer){
        try{$srv=Open-GarageServer $state.LocalServer;try{$pl=@(Get-GarageServerPlayers $srv $catalog|Where-Object Slot -eq $slot)[0];if($pl){$cur=$pl.Current}}finally{Close-GarageHelper $srv}}catch{}
    }elseif($state.Current){$cur=$state.Current}
    $hold=if($state.Desired.ContainsKey($slot)){' · wird gehalten'}else{''}
    $lblWho.Text=('Dein Auto · Spieler {0} ({1}){2}{3}' -f $slot,$role,$(if($cur){' · aktuell '+$cur}else{''}),$hold)
}

function Set-ServerSlot([int]$Slot,[uint32]$Key){
    $srv=Open-GarageServer $state.LocalServer
    try{
        $pl=@(Get-GarageServerPlayers $srv $catalog|Where-Object Slot -eq $Slot)[0]
        if(!$pl){throw ('Spieler {0} ist gerade nicht im Rennen.' -f $Slot)}
        if($pl.Key -ne $Key){[void](Set-GarageServerPlayerCar $srv $pl $Key $catalog)}
        $state.Desired[$Slot]=$Key
    }finally{Close-GarageHelper $srv}
}

function Apply-Key([uint32]$Key,[string]$Label){
    try{
        Update-Identity
        if($state.Slot -eq $null){throw 'Dein Spieler ist noch nicht im Rennen.'}
        if($Key -eq 0){
            if($state.LocalServer){$state.Desired.Remove($state.Slot);Set-Status 'Auto wird nicht mehr gehalten – die Story wählt wieder selbst.' $C.Ok}
            else{Set-Status 'Story-Auto: nur der Host kann das Halten beenden (oder einfach ein anderes Auto wählen).' $C.Muted}
            return
        }
        if($state.LocalServer){Set-ServerSlot $state.Slot $Key}
        elseif($state.HostIp){Send-GarageRelayRequest $state.HostIp $state.Slot $Key;$state.Desired[$state.Slot]=$Key;$state.Current=$state.Variant.DatabaseEntry}
        else{throw 'Host-Adresse unbekannt.'}
        Save-GarageLastSelection $state.Car.Id $state.Pack.Pack $state.Variant.N
        Set-Status ('Übernommen: '+$Label+' – kommt beim nächsten Etappenstart und wird gehalten (Fenster offen lassen).') $C.Ok
        Update-Identity
    }catch{Set-Status $_.Exception.Message $C.Bad}
}

$txtSearch.Add_TextChanged({Fill-List})
$lst.Add_SelectedIndexChanged({if($lst.SelectedItem -and $lst.SelectedItem -ne $state.Car){Select-Car $lst.SelectedItem 'stock' 1}})
$btnApply.Add_Click({if($state.Variant){Apply-Key ([uint32]$state.Variant.VehicleKey) ($state.Car.Name+' · '+$state.Pack.Label+' '+$state.Variant.N)}})
$btnStory.Add_Click({Apply-Key 0 'Story-Auto'})
$btnImage.Add_Click({
    if(!$state.Variant){return}
    $dlg=New-Object Windows.Forms.OpenFileDialog;$dlg.Filter='Bilder|*.png;*.jpg;*.jpeg;*.bmp'
    if($dlg.ShowDialog($form) -eq 'OK'){
        try{[void](Save-GaragePreview $dlg.FileName $state.Variant.DatabaseEntry);Show-Preview}catch{Set-Status $_.Exception.Message $C.Bad}
    }
})
$btnShot.Add_Click({
    if(!$state.Variant){return}
    $g=Get-OwnGame
    if(!$g){Set-Status 'Kein Spiel gefunden.' $C.Bad;return}
    try{[void](Save-GarageGameCapture $g.Id $state.Variant.DatabaseEntry);Show-Preview;Set-Status 'Vorschaubild aus dem Spiel gespeichert.' $C.Ok}catch{Set-Status $_.Exception.Message $C.Bad}
})
$form.AllowDrop=$true;$pic.AllowDrop=$true
$dragEnter={param($s,$e)if($e.Data.GetDataPresent([Windows.Forms.DataFormats]::FileDrop)){$e.Effect='Copy'}}
$dragDrop={param($s,$e)
    try{
        $file=@($e.Data.GetData([Windows.Forms.DataFormats]::FileDrop))[0]
        if($state.Car -and $file){[void](Save-GaragePreview $file $state.Car.Id);Remove-Item -LiteralPath (Join-Path (Join-Path (Get-GarageDataDirectory) 'previews') ($state.Car.Id+'.credit.txt')) -ErrorAction SilentlyContinue;Show-Preview;Set-Status 'Eigenes Vorschaubild gespeichert.' $C.Ok}
    }catch{Set-Status $_.Exception.Message $C.Bad}}
$form.Add_DragEnter($dragEnter);$form.Add_DragDrop($dragDrop);$pic.Add_DragEnter($dragEnter);$pic.Add_DragDrop($dragDrop)
$form.Add_FormClosed({if($state.Listener){$state.Listener.Stop()};if($pic.Image){$pic.Image.Dispose()}})

Fill-List
$last=Read-GarageLastSelection
$startCar=if($last){@($catalog.Cars|Where-Object Id -eq $last.CarId)[0]}else{$null}
if(!$startCar){$startCar=$catalog.Cars[0]}
Select-Car $startCar ($(if($last){[string]$last.Pack}else{'stock'})) ($(if($last){[int]$last.N}else{1}))
$lst.SelectedItem=$startCar

if($SelfTest){
    $total=($catalog.Cars|ForEach-Object{$_.Packs}|ForEach-Object{$_.Variants}).Count
    "SELFTEST ok cars=$($catalog.Cars.Count) variants=$total packs=$($packs.Controls.Count) variantButtons=$($vars.Controls.Count) selected=$($state.Variant.DatabaseEntry)"
    if($Screenshot){
        $form.Left=-3000;$form.Show();[Windows.Forms.Application]::DoEvents()
        $bmp=New-Object Drawing.Bitmap($form.Width,$form.Height);$form.DrawToBitmap($bmp,(New-Object Drawing.Rectangle(0,0,$form.Width,$form.Height)))
        $bmp.Save($Screenshot,[Drawing.Imaging.ImageFormat]::Png);$bmp.Dispose();$form.Hide()
    }
    $form.Dispose();exit 0
}
$timer=New-Object Windows.Forms.Timer;$timer.Interval=1000
$timer.Add_Tick({
    try{
        $script:tick=1+[int]$script:tick
        if($script:tick % 3 -eq 1){Update-Identity}
        if($state.LocalServer){
            if($state.Listener){
                $own=if($state.Slot -ne $null){[int]$state.Slot}else{-1}
                [void](Receive-GarageRelayRequests $state.Listener $own {
                    param($slot,$key)
                    try{Set-ServerSlot $slot $key;Set-Status ('Gast (Spieler '+$slot+') hat ein Auto gewählt.') $C.Ok;'OK'}catch{$_.Exception.Message}
                })
            }
            if($state.Desired.Count){
                $srv=Open-GarageServer $state.LocalServer
                try{$fix=Sync-GarageServerDesired $srv $state.Desired $catalog}finally{Close-GarageHelper $srv}
                if($fix.Count){Set-Status ('Auto für Spieler '+($fix -join ', ')+' erneut gesetzt (Retry/Checkpoint).') $C.Ok}
            }
        }
    }catch{Set-Status $_.Exception.Message $C.Bad}
})
$form.Add_Shown({Update-Identity;$timer.Start()})
$form.Add_FormClosing({$timer.Stop()})
[void]$form.ShowDialog()
