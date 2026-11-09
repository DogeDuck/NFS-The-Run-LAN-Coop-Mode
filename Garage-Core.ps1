#requires -Version 7.0
# Koop-Garage: Katalog + Laufzeit-Vorgabe des LAN-Helpers im EIGENEN laufenden Spiel.
# Schreibt genau 4 Byte (Fahrzeug-Kennung) in das geladene NFSTR_LANOnlineHelper.asi
# nach Pruefung von Prozessname, 32-Bit, Modulname, ASI-SHA256 und plausiblem Altwert.
# Keine Spielstand-, INI- oder EXE-Aenderung.

$script:GarageHelperSha = '04C08719749BED0FD0F79D190DC02EB0ED85957677EFAA1F5F54C825FCF85002'
$script:GarageHelperOffset = 0x15B74
$script:GarageProcessName = 'Need For Speed The Run'

if(-not ('CoopGarage.Native' -as [type])){
Add-Type -Namespace CoopGarage -Name Native -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool CloseHandle(IntPtr h);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool IsWow64Process(IntPtr h, out bool wow);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out IntPtr read);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool WriteProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out IntPtr written);
[DllImport("psapi.dll", SetLastError=true)] public static extern bool EnumProcessModulesEx(IntPtr h, [Out] IntPtr[] mods, int cb, out int needed, uint filter);
[DllImport("psapi.dll", SetLastError=true, CharSet=CharSet.Unicode)] public static extern uint GetModuleFileNameExW(IntPtr h, IntPtr mod, System.Text.StringBuilder name, int size);
[StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
'@
}

function Get-GarageCatalog([string]$Path=(Join-Path $PSScriptRoot 'Garage-Cars.json')){
    if((Get-Item -LiteralPath $Path).Length -gt 2MB){throw 'Garage-Katalog ist zu gross.'}
    $cars=Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json -ErrorAction Stop
    $keys=@{}
    foreach($car in $cars){
        if($car.Id -notmatch '^[A-Za-z0-9_-]{1,24}$' -or !$car.Name){throw 'Ungueltiger Garage-Eintrag.'}
        foreach($pack in $car.Packs){foreach($v in $pack.Variants){
            $k=[uint32]$v.VehicleKey
            if($k -eq 0 -or $keys.ContainsKey($k)){throw 'Ungueltige oder doppelte Fahrzeug-Kennung.'}
            if($v.DatabaseEntry -notmatch '^[a-z0-9_]{3,64}$'){throw 'Ungueltiger Datenbankname.'}
            $keys[$k]=$v
        }}
    }
    return [pscustomobject]@{Cars=@($cars);Keys=$keys}
}

function Get-GarageGameProcesses{
    @(Get-Process -Name $script:GarageProcessName -ErrorAction SilentlyContinue | Sort-Object StartTime)
}

function Find-GarageModule([IntPtr]$Handle,[string]$Name){
    $mods=New-Object IntPtr[] 1024;$needed=0
    if(![CoopGarage.Native]::EnumProcessModulesEx($Handle,$mods,$mods.Length*[IntPtr]::Size,[ref]$needed,1)){throw 'Module des Spiels nicht lesbar.'}
    $count=[Math]::Min($mods.Length,[int]($needed/[IntPtr]::Size))
    $found=$null
    for($i=0;$i -lt $count;$i++){
        $sb=New-Object Text.StringBuilder 1024
        [void][CoopGarage.Native]::GetModuleFileNameExW($Handle,$mods[$i],$sb,1024)
        if([IO.Path]::GetFileName($sb.ToString()) -ieq $Name){
            if($found){throw ($Name+' mehrfach geladen.')}
            $found=[pscustomobject]@{Base=$mods[$i];Path=$sb.ToString()}
        }
    }
    return $found
}

function Open-GarageHelper([int]$ProcessId){
    $p=Get-Process -Id $ProcessId -ErrorAction Stop
    if($p.ProcessName -ne $script:GarageProcessName){throw 'Das ist kein The-Run-Prozess.'}
    $h=[CoopGarage.Native]::OpenProcess(0x0438,$false,$ProcessId)   # QUERY_INFORMATION|VM_OPERATION|VM_READ|VM_WRITE
    if($h -eq [IntPtr]::Zero){throw 'Kein Zugriff auf das Spiel (gleiche Rechte wie das Spiel noetig).'}
    try{
        $wow=$false
        if(![CoopGarage.Native]::IsWow64Process($h,[ref]$wow) -or !$wow){throw 'Unerwarteter Spielprozess (nicht 32-Bit).'}
        $found=Find-GarageModule $h 'NFSTR_LANOnlineHelper.asi'
        if(!$found){throw 'LAN-Helper ist in diesem Spiel nicht geladen.'}
        $sha=(Get-FileHash -LiteralPath $found.Path -Algorithm SHA256).Hash
        if($sha -ne $script:GarageHelperSha){throw 'Unbekannte LAN-Helper-Version; Garage nicht freigegeben.'}
        return [pscustomobject]@{Handle=$h;ProcessId=$ProcessId;Address=[IntPtr]($found.Base.ToInt64()+$script:GarageHelperOffset)}
    }catch{[void][CoopGarage.Native]::CloseHandle($h);throw}
}

function Close-GarageHelper($Helper){if($Helper -and $Helper.Handle -ne [IntPtr]::Zero){[void][CoopGarage.Native]::CloseHandle($Helper.Handle)}}

function Read-GarageForcedKey($Helper){
    $buf=New-Object byte[] 4;$n=[IntPtr]::Zero
    if(![CoopGarage.Native]::ReadProcessMemory($Helper.Handle,$Helper.Address,$buf,4,[ref]$n) -or $n.ToInt64() -ne 4){throw 'Aktuelle Vorgabe nicht lesbar.'}
    return [BitConverter]::ToUInt32($buf,0)
}

function Set-GarageForcedKey($Helper,[uint32]$Key,$Catalog,[uint32[]]$ExtraKnown=@()){
    if($Key -ne 0 -and !$Catalog.Keys.ContainsKey($Key)){throw 'Kennung steht nicht im Garage-Katalog.'}   # 0 = Story-Auto
    $old=Read-GarageForcedKey $Helper
    if($old -ne 0 -and !$Catalog.Keys.ContainsKey($old) -and $old -notin $ExtraKnown){
        throw ('Unerwarteter Altwert 0x{0:X8}; nichts geschrieben.' -f $old)
    }
    $buf=[BitConverter]::GetBytes($Key);$n=[IntPtr]::Zero
    if(![CoopGarage.Native]::WriteProcessMemory($Helper.Handle,$Helper.Address,$buf,4,[ref]$n) -or $n.ToInt64() -ne 4){throw 'Schreiben fehlgeschlagen.'}
    if((Read-GarageForcedKey $Helper) -ne $Key){throw 'Kontrolle nach dem Schreiben fehlgeschlagen.'}
    return $old
}

function Get-GarageDataDirectory{
    if(!$env:LOCALAPPDATA){throw 'LOCALAPPDATA fehlt.'}
    $d=Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop'
    if(!(Test-Path -LiteralPath $d)){[void](New-Item -ItemType Directory -Path $d)}
    return $d
}

function Get-GaragePreviewPath([string]$Entry,[string]$CarId){
    $dir=Join-Path (Get-GarageDataDirectory) 'previews'
    foreach($name in @($Entry,$CarId)){
        foreach($ext in '.png','.jpg','.jpeg','.bmp'){
            $p=Join-Path $dir ($name+$ext)
            if(Test-Path -LiteralPath $p){return $p}
        }
    }
    return $null
}

function Save-GaragePreview([string]$Source,[string]$Name){
    if($Name -notmatch '^[A-Za-z0-9_-]{1,64}$'){throw 'Ungueltiger Bildname.'}
    $ext=[IO.Path]::GetExtension($Source).ToLowerInvariant()
    if($ext -notin '.png','.jpg','.jpeg','.bmp'){throw 'Nur PNG, JPG oder BMP.'}
    if((Get-Item -LiteralPath $Source).Length -gt 20MB){throw 'Bild ist zu gross.'}
    $dir=Join-Path (Get-GarageDataDirectory) 'previews'
    if(!(Test-Path -LiteralPath $dir)){[void](New-Item -ItemType Directory -Path $dir)}
    Get-ChildItem -LiteralPath $dir -Filter ($Name+'.*') | Remove-Item
    $target=Join-Path $dir ($Name+$ext)
    Copy-Item -LiteralPath $Source -Destination $target
    return $target
}

function Read-GarageLastSelection{
    $p=Join-Path (Get-GarageDataDirectory) 'garage-selection.json'
    if(!(Test-Path -LiteralPath $p) -or (Get-Item -LiteralPath $p).Length -gt 4096){return $null}
    try{return Get-Content -LiteralPath $p -Raw -Encoding utf8 | ConvertFrom-Json}catch{return $null}
}

function Save-GarageLastSelection([string]$CarId,[string]$Pack,[int]$N){
    $p=Join-Path (Get-GarageDataDirectory) 'garage-selection.json'
    $tmp=$p+'.tmp'
    [IO.File]::WriteAllText($tmp,(@{Schema=1;CarId=$CarId;Pack=$Pack;N=$N}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $p -Force
}

function Save-GarageGameCapture([int]$ProcessId,[string]$Name){
    # Nur Bildschirmfoto des Spielfensters (keine Eingaben ans Spiel).
    if($Name -notmatch '^[A-Za-z0-9_-]{1,64}$'){throw 'Ungueltiger Bildname.'}
    $p=Get-Process -Id $ProcessId -ErrorAction Stop
    if($p.ProcessName -ne $script:GarageProcessName -or $p.MainWindowHandle -eq [IntPtr]::Zero){throw 'Spielfenster nicht gefunden.'}
    if([CoopGarage.Native]::IsIconic($p.MainWindowHandle)){throw 'Spielfenster ist minimiert.'}
    $r=New-Object CoopGarage.Native+RECT
    if(![CoopGarage.Native]::GetWindowRect($p.MainWindowHandle,[ref]$r)){throw 'Fenstergroesse nicht lesbar.'}
    $w=$r.Right-$r.Left;$h=$r.Bottom-$r.Top
    if($w -lt 64 -or $h -lt 64){throw 'Spielfenster zu klein.'}
    Add-Type -AssemblyName System.Drawing
    $bmp=New-Object Drawing.Bitmap($w,$h)
    try{
        $g=[Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen($r.Left,$r.Top,0,0,$bmp.Size);$g.Dispose()
        $dir=Join-Path (Get-GarageDataDirectory) 'previews'
        if(!(Test-Path -LiteralPath $dir)){[void](New-Item -ItemType Directory -Path $dir)}
        Get-ChildItem -LiteralPath $dir -Filter ($Name+'.*') | Remove-Item
        $target=Join-Path $dir ($Name+'.png')
        $bmp.Save($target,[Drawing.Imaging.ImageFormat]::Png)
        return $target
    }finally{$bmp.Dispose()}
}

# ---------------- Server-Modus (Story-Auto pro Spieler) ----------------
# Der Server holt das Spielerauto in 13EAF90: ohne Debug-Liste gilt [Spieler + [2731FE4] + E0].
# Aufrufer 13CDBB0/13D6320 (Fahrzeug-Spawn). Pro Spieler, bleibt bis die Story ein neues setzt.
# Schreibt genau 4 Byte in diesen Spieler-Wert. Nur auf dem PC, auf dem NFSTR_Server.exe laeuft (Host).
$script:GarageServerBuilds=@('4AFB76C21D08439778DBA038AD787618F752AA3C639A18A07A5B1672C0263C9D',
 'DCFAFC833016BAADE51F556C82963BA8C015406ADC69BEA0006919AD7DD68695','79368D76F6967918C2AE0208757546AA5A0E197B8EE9BFDB631ED809F15AC79E',
 '22F1604CC40643DBCB18154CDA3DA627A63F0B34A4DFDFD7631AD99C9A81B768','76F2D6DDDBBEAE3C6FDA85644C4D9D65ED7551AB6542AD4D08750EA4F2C04A92',
 '2BBD8E66B7E5219CF72C7CCCA06404AA2C36712F2B58E4CFEFCAA53C1082066C','AEAF9C120B02A158CD3F52554FBFA1F2F0F18507DA43D9C4AA00225C845249FF',
 'B4DFA348819BCAC31872095E6959AA9BAF07C143E8543CA8E32BB4CEE40EBD0C')
$script:GarageServerGetter='a130638e028b50042b10740c8b0050e84c199cff83c404c38b81e0000000c3'
$script:GarageServerShaCache=@{}

function Read-GarageU32($Handle,[int64]$Address){
    $b=New-Object byte[] 4;$n=[IntPtr]::Zero
    if(![CoopGarage.Native]::ReadProcessMemory($Handle,[IntPtr]$Address,$b,4,[ref]$n) -or $n.ToInt64() -ne 4){throw ('Speicher nicht lesbar bei 0x{0:X8}.' -f $Address)}
    return [BitConverter]::ToUInt32($b,0)
}

function Get-GarageServerProcesses{@(Get-Process -Name 'NFSTR_Server' -ErrorAction SilentlyContinue)}

function Open-GarageServer([int]$ProcessId){
    $p=Get-Process -Id $ProcessId -ErrorAction Stop
    if($p.ProcessName -ne 'NFSTR_Server'){throw 'Das ist kein The-Run-Server.'}
    $path=$p.MainModule.FileName
    if(!$script:GarageServerShaCache.ContainsKey($path)){$script:GarageServerShaCache[$path]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
    if($script:GarageServerShaCache[$path] -notin $script:GarageServerBuilds){throw 'Unbekannte Server-Version; Server-Modus nicht freigegeben.'}
    $h=[CoopGarage.Native]::OpenProcess(0x0438,$false,$ProcessId)
    if($h -eq [IntPtr]::Zero){throw 'Kein Zugriff auf den Server.'}
    try{
        $wow=$false
        if(![CoopGarage.Native]::IsWow64Process($h,[ref]$wow) -or !$wow){throw 'Unerwarteter Serverprozess (nicht 32-Bit).'}
        $code=New-Object byte[] 31;$n=[IntPtr]::Zero
        if(![CoopGarage.Native]::ReadProcessMemory($h,[IntPtr]0x13EAF90,$code,31,[ref]$n)){throw 'Server-Code nicht lesbar.'}
        $hex=-join ($code|ForEach-Object{$_.ToString('x2')})
        if($hex -ne $script:GarageServerGetter){throw 'Server-Autovorgabe ist umgeleitet (ForceServerPlayersCarHash aktiv?). Bitte im Helper auf 0 setzen.'}
        $off=Read-GarageU32 $h 0x2731FE4
        if($off -lt 4 -or $off -gt 0x10000){throw 'Unerwarteter Spieler-Offset.'}
        return [pscustomobject]@{Handle=$h;ProcessId=$ProcessId;Offset=[int64]$off}
    }catch{[void][CoopGarage.Native]::CloseHandle($h);throw}
}

function Get-GarageServerPlayers($Server,$Catalog){
    $mgr=Read-GarageU32 $Server.Handle 0x28A3220
    if(!$mgr){return @()}
    $arr=Read-GarageU32 $Server.Handle ($mgr+0xA4)
    if(!$arr){return @()}
    $out=@()
    for($i=0;$i -lt 8;$i++){
        $p=Read-GarageU32 $Server.Handle ($arr+4*$i)
        if(!$p){continue}
        $flag=New-Object byte[] 1;$fn=[IntPtr]::Zero
        if(![CoopGarage.Native]::ReadProcessMemory($Server.Handle,[IntPtr]([int64]$p+0x260),$flag,1,[ref]$fn) -or $flag[0] -ne 0){continue}   # nur Menschen (Player+260 == 0)
        $addr=[int64]$p+$Server.Offset+0xE0
        try{$k=Read-GarageU32 $Server.Handle $addr}catch{continue}
        if($k -eq 0){continue}
        $name=if($Catalog.Keys.ContainsKey([uint32]$k)){$Catalog.Keys[[uint32]$k].DatabaseEntry}else{'0x{0:X8}' -f $k}
        $out+=[pscustomobject]@{Slot=$i;Player=[int64]$p;Address=$addr;Key=[uint32]$k;Current=$name}
    }
    return $out
}

function Set-GarageServerPlayerCar($Server,$Player,[uint32]$Key,$Catalog){
    if(!$Catalog.Keys.ContainsKey($Key)){throw 'Kennung steht nicht im Garage-Katalog.'}
    $now=Read-GarageU32 $Server.Handle $Player.Address
    if($now -ne $Player.Key){throw 'Spieler-Auto hat sich inzwischen geaendert; bitte neu suchen.'}
    $buf=[BitConverter]::GetBytes($Key);$n=[IntPtr]::Zero
    if(![CoopGarage.Native]::WriteProcessMemory($Server.Handle,[IntPtr]$Player.Address,$buf,4,[ref]$n) -or $n.ToInt64() -ne 4){throw 'Schreiben fehlgeschlagen.'}
    if((Read-GarageU32 $Server.Handle $Player.Address) -ne $Key){throw 'Kontrolle nach dem Schreiben fehlgeschlagen.'}
    $Player.Key=$Key
    return $now
}

function Sync-GarageServerDesired($Server,[hashtable]$Desired,$Catalog){
    # Setzt die gemerkte Wahl erneut, wenn Retry/Checkpoint den Wert zurueckgesetzt hat.
    $changed=@()
    foreach($pl in Get-GarageServerPlayers $Server $Catalog){
        if(!$Desired.ContainsKey($pl.Slot)){continue}
        $want=[uint32]$Desired[$pl.Slot]
        if($pl.Key -eq $want){continue}
        [void](Set-GarageServerPlayerCar $Server $pl $want $Catalog)
        $changed+=$pl.Slot
    }
    return $changed
}

# ---------------- Eigenes Auto: Spieler-Nummer + Weiterleitung Gast -> Host ----------------
$script:GarageRelayPort=25211

function Get-GarageClientPlayerId([int]$ProcessId){
    # Lokaler Spieler des EIGENEN Spiels: [[[2888F78]+BC]+334] (wie coop_diagnostics).
    $p=Get-Process -Id $ProcessId -ErrorAction Stop
    if($p.ProcessName -ne $script:GarageProcessName){throw 'Das ist kein The-Run-Prozess.'}
    $h=[CoopGarage.Native]::OpenProcess(0x0410,$false,$ProcessId)
    if($h -eq [IntPtr]::Zero){throw 'Kein Zugriff auf das Spiel.'}
    try{
        $mgr=Read-GarageU32 $h 0x2888F78; if(!$mgr){return $null}
        $pl=Read-GarageU32 $h ($mgr+0xBC); if(!$pl){return $null}
        $id=Read-GarageU32 $h ($pl+0x334)
        if($id -gt 63){return $null}
        return [int]$id
    }catch{return $null}finally{[void][CoopGarage.Native]::CloseHandle($h)}
}

function Get-GarageClientServerIp([int]$ProcessId){
    $cmd=(Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId").CommandLine
    if($cmd -match '-Client\.ServerIp\s+(\d{1,3}(?:\.\d{1,3}){3})'){return $Matches[1]}
    return $null
}

function Send-GarageRelayRequest([string]$HostIp,[int]$Slot,[uint32]$Key,[int]$Port=25211){
    $tcp=New-Object Net.Sockets.TcpClient
    try{
        $task=$tcp.ConnectAsync($HostIp,$Port)
        if(!$task.Wait(2000) -or !$tcp.Connected){throw 'Host-Garage nicht erreichbar (Fenster beim Host offen? Firewall TCP 25211?).'}
        $tcp.ReceiveTimeout=3000
        $s=$tcp.GetStream();$w=New-Object IO.StreamWriter($s);$r=New-Object IO.StreamReader($s)
        $w.WriteLine((@{v=1;slot=$Slot;key=$Key}|ConvertTo-Json -Compress));$w.Flush()
        $answer=$r.ReadLine()
        if($answer -ne 'OK'){throw ('Host lehnt ab: '+$answer)}
    }finally{$tcp.Dispose()}
}

function Start-GarageRelayListener([int]$Port=25211){
    $l=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Any,$Port)
    $l.Start()
    return $l
}

function Receive-GarageRelayRequests($Listener,[int]$OwnSlot,[scriptblock]$Apply){
    # Nicht blockierend: verarbeitet wartende Anfragen. Der eigene (Host-)Slot ist von aussen gesperrt.
    $done=@()
    while($Listener.Pending()){
        # Apply runs in PowerShell's dynamic scope. Do not name this $c: the GUI
        # palette $C would then resolve to this TcpClient inside Set-Status.
        $relayClient=$Listener.AcceptTcpClient()
        try{
            $relayClient.ReceiveTimeout=2000
            $s=$relayClient.GetStream();$r=New-Object IO.StreamReader($s);$w=New-Object IO.StreamWriter($s)
            $line=$r.ReadLine()
            if(!$line -or $line.Length -gt 200){$w.WriteLine('ungueltig');$w.Flush();continue}
            $req=$line|ConvertFrom-Json
            if($req.v -ne 1 -or $req.slot -isnot [long] -and $req.slot -isnot [int]){$w.WriteLine('ungueltig');$w.Flush();continue}
            $slot=[int]$req.slot
            if($slot -eq $OwnSlot -or $slot -lt 0 -or $slot -gt 63){$w.WriteLine('fremder Slot');$w.Flush();continue}
            $msg=& $Apply $slot ([uint32]$req.key)
            $w.WriteLine($msg);$w.Flush()
            $done+=$slot
        }catch{}finally{$relayClient.Dispose()}
    }
    return $done
}

# ---------------- Vorschaubilder aus dem NFS-Wiki (vom Nutzer selbst gespeichert) ----------------
function Get-GarageWikiPage($Car){
    $p=Join-Path $PSScriptRoot 'Garage-Wiki.json'
    if(Test-Path -LiteralPath $p){
        $w=Get-Content -LiteralPath $p -Raw -Encoding utf8|ConvertFrom-Json
        $u=$w.Pages.($Car.Id)
        if($u -match '^https://nfs\.fandom\.com/wiki/'){return $u}
    }
    return 'https://nfs.fandom.com/wiki/Special:Search?query='+[Uri]::EscapeDataString($Car.Name+' The Run')
}

function Save-GarageWikiPreview([string]$Source,$Car){
    # Bild gilt fuer das ganze Auto (alle Varianten ohne eigenes Bild) und bekommt einen Credit.
    $target=Save-GaragePreview $Source $Car.Id
    $credit=Join-Path (Split-Path $target) ($Car.Id+'.credit.txt')
    [IO.File]::WriteAllText($credit,('Bild: Need for Speed Wiki (Fandom) – '+(Get-GarageWikiPage $Car)),[Text.UTF8Encoding]::new($false))
    return $target
}

function Get-GaragePreviewCredit([string]$Path){
    if(!$Path){return ''}
    $name=[IO.Path]::GetFileNameWithoutExtension($Path)
    $c=Join-Path (Split-Path $Path) ($name+'.credit.txt')
    if(Test-Path -LiteralPath $c){return (Get-Content -LiteralPath $c -Raw -Encoding utf8).Trim()}
    return ''
}

# ---------------- Automatische Fotos (Wikipedia / Wikimedia Commons, freie Lizenzen) ----------------
$script:GaragePhotos=$null
function Get-GaragePhotoInfo($Car){
    if($script:GaragePhotos -eq $null){
        $p=Join-Path $PSScriptRoot 'Garage-Photos.json'
        $script:GaragePhotos=if(Test-Path -LiteralPath $p){(Get-Content -LiteralPath $p -Raw -Encoding utf8|ConvertFrom-Json).Photos}else{[pscustomobject]@{}}
    }
    $i=$script:GaragePhotos.($Car.Id)
    if($i -and $i.Url -match '^https://upload\.wikimedia\.org/'){return $i}
    return $null
}

function Start-GaragePhotoDownload($Car,[scriptblock]$Done){
    # Asynchron (Fenster friert nicht ein). Speichert <CarId>.jpg + Credit-Datei.
    $info=Get-GaragePhotoInfo $Car; if(!$info){return $false}
    $dir=Join-Path (Get-GarageDataDirectory) 'previews'
    if(!(Test-Path -LiteralPath $dir)){[void](New-Item -ItemType Directory -Path $dir)}
    $target=Join-Path $dir ($Car.Id+'.jpg');$tmp=$target+'.part'
    $wc=New-Object Net.WebClient
    $wc.Headers.Add('User-Agent','TheRunCoopGarage/1.0 (private mod tool)')
    $credit='Foto: '+$info.Artist+' · '+$info.License+' · Wikimedia Commons ('+$info.Article+')'
    $wc.add_DownloadFileCompleted({param($s,$e)
        try{
            if(!$e.Error -and (Get-Item -LiteralPath $tmp).Length -gt 1000){
                Move-Item -LiteralPath $tmp -Destination $target -Force
                [IO.File]::WriteAllText((Join-Path $dir ($Car.Id+'.credit.txt')),$credit,[Text.UTF8Encoding]::new($false))
            }else{Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue}
        }catch{}
        $s.Dispose();& $Done
    }.GetNewClosure())
    $wc.DownloadFileAsync([Uri]$info.Url,$tmp)
    return $true
}
