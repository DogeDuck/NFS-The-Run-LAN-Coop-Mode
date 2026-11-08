#requires -Version 7.0
# Shared personal UI language. Never sent to the game server or written to a game INI.
$script:CoopStrings=@{
    en=@{
        Title='NFS The Run – Co-op'; Story='CO-OP STORY'; Language='Language / Sprache'; Host='Host'; Guest='Join'; Solo='Solo'
        Nickname='Player name'; HostIp='Host IPv4 (Radmin/VPN, remembered)'; GameDirectory='Game folder'; Browse='Browse'; HostOptions='HOST SETTINGS'
        MaxPlayers='Max. players'; ShowServer='Show server window'; Background='Image…'; StartHost='Start as host'; StartGuest='Connect'; StartSolo='Start single player'
        HostHint='Server limit: 1–4; only 2 players tested so far. Each player chooses their car in the garage.'
        GuestHint='The host sets shared game options. Your language, name, car and window preferences stay personal.'
        SoloHint='Single player with the installed mods. Co-op is disabled for this session; normal game saving remains active.'
        DifficultyPending='Difficulty: set in game. Automatic host-to-guest sync is still pending.'
        DifficultySolo='Difficulty: choose in the game. Launcher control is not available yet.'
        ChooseExe='Select Need For Speed The Run.exe'; ExeFilter='Game executable|Need For Speed The Run.exe'; ChooseBackground='Choose a background (stored only on this PC)'; ImageFilter='Images|*.jpg;*.jpeg;*.png;*.bmp'
        MissingStarter='Start-Coop.ps1 is missing from this package.'; MissingGame='Select the game folder containing Need For Speed The Run.exe.'; Running='The Run or the co-op server is already running.'
        BadNickname='Player name: 1–16 letters (A–Z), digits, _ or -.'; BadIp='Enter the host IPv4 address without a port.'; GarageHint='Choose your car in the garage window that opens with the game.'
        GarageTitle='Car selection'; ConnectionTitle='Co-op connection'; BackgroundTitle='Background'; StartFailed='Start failed. Press Enter to close'; VpnPrompt='Host Radmin/VPN IPv4'
        StartCar='Starting car: {0}'; ViewCars='Before racing, open VIEW CARS once in the main menu, then return and start the race. Keep avoiding gas stations.'
        GarageFailed='Could not open the garage: {0}'; YourIp='Your Radmin IP: {0}'; Invite='Other players: open Launch-Coop.cmd on your PC and choose Join.'
        ReadyPrompt='Press Enter when all guest game windows are open'; HostClosed='The host game window was closed.'; ServerStarted='Server started. Once everyone is connected, only the host chooses THE RUN → Continue.'
        GuestWaiting='Wait for the connection in the game. The host starts the server and chooses Continue.'; Saved='Save backed up before starting: {0}'; LeaveOpen='Keep this launcher window open until the game ends.'
        BackupFailed='Save backup verification failed.'; FolderPrompt='Full game folder (containing the game executable)'; BackupProtected='THERUNBACKUP cannot be used.'
        CloseGame='Close the game and test server first.'; CoopMissing='Co-op files are missing or modified. Run Install.cmd.'; LanFile='LAN base file is missing or modified: {0}'
        D3dActive='d3d11.dll is still active. Check the installation.'; ProcessChanged='This process ID no longer belongs to this co-op session.'
        UnknownCar='This starting car is not available.'; CarFile='Car preferences could not be read. Check car-preferences.json.'
    }
    de=@{
        Title='NFS The Run – Koop'; Story='KOOP-STORY'; Language='Language / Sprache'; Host='Hosten'; Guest='Beitreten'; Solo='Solo'
        Nickname='Spielername'; HostIp='Host-IPv4 (Radmin/VPN, wird gemerkt)'; GameDirectory='Spielordner'; Browse='Auswählen'; HostOptions='HOST-EINSTELLUNGEN'
        MaxPlayers='Max. Spieler'; ShowServer='Serverfenster anzeigen'; Background='Bild…'; StartHost='Als Host starten'; StartGuest='Verbinden'; StartSolo='Einzelspieler starten'
        HostHint='Server-Vorgabe: 1–4; bisher nur 2 Spieler getestet. Jeder wählt sein Auto im Garage-Fenster.'
        GuestHint='Gemeinsame Spieloptionen legt der Host fest. Sprache, Name, Auto und Fenster bleiben persönlich.'
        SoloHint='Einzelspieler mit den installierten Mods. Koop ist für diese Sitzung aus; normales Speichern im Spiel bleibt aktiv.'
        DifficultyPending='Schwierigkeit: im Spiel wählen. Automatische Übernahme vom Host steht noch aus.'
        DifficultySolo='Schwierigkeit im Spiel wählen. Launcher-Auswahl ist noch nicht verfügbar.'
        ChooseExe='Need For Speed The Run.exe auswählen'; ExeFilter='Spiel-EXE|Need For Speed The Run.exe'; ChooseBackground='Hintergrundbild wählen (bleibt nur auf diesem PC)'; ImageFilter='Bilder|*.jpg;*.jpeg;*.png;*.bmp'
        MissingStarter='Start-Coop.ps1 fehlt im Paket.'; MissingGame='Bitte den Spielordner mit Need For Speed The Run.exe auswählen.'; Running='The Run oder der Koop-Server läuft bereits.'
        BadNickname='Spielername: 1–16 Buchstaben (A–Z), Ziffern, _ oder -.'; BadIp='Bitte die IPv4 des Hosts ohne Port eintragen.'; GarageHint='Dein Auto wählst du im Garage-Fenster, das mit dem Spiel startet.'
        GarageTitle='Autoauswahl'; ConnectionTitle='Koop-Verbindung'; BackgroundTitle='Hintergrund'; StartFailed='Start fehlgeschlagen. Enter zum Schließen'; VpnPrompt='Radmin-/VPN-IPv4 des Hosts'
        StartCar='Startauto: {0}'; ViewCars='Vor dem Rennen im Hauptmenü einmal VIEW CARS / AUTOS ANSEHEN öffnen. Danach zurück und Rennen starten. Tankstellen weiterhin meiden.'
        GarageFailed='Garage-Fenster konnte nicht starten: {0}'; YourIp='Deine Radmin-IP: {0}'; Invite='Mitspieler: Launch-Coop.cmd am eigenen PC öffnen und Beitreten wählen.'
        ReadyPrompt='Enter drücken, sobald die Spielfenster aller Gäste offen sind'; HostClosed='Das Host-Spielfenster wurde geschlossen.'; ServerStarted='Server gestartet. Sobald alle verbunden sind, wählt nur der Host THE RUN → Fortsetzen.'
        GuestWaiting='Im Spiel auf die Verbindung warten. Der Host startet den Server und wählt Fortsetzen.'; Saved='Spielstand vor dem Start gesichert in: {0}'; LeaveOpen='Dieses Starterfenster offen lassen, bis das Spiel beendet ist.'
        BackupFailed='Prüfung der Spielstandssicherung fehlgeschlagen.'; FolderPrompt='Vollständiger Spielordner (enthält die Spiel-EXE)'; BackupProtected='THERUNBACKUP wird nicht verwendet.'
        CloseGame='Bitte Spiel und Testserver zuerst schließen.'; CoopMissing='Koop-Dateien fehlen oder wurden verändert. Bitte Install.cmd ausführen.'; LanFile='LAN-Grunddatei fehlt oder ist verändert: {0}'
        D3dActive='d3d11.dll ist noch aktiv. Bitte die Installation prüfen.'; ProcessChanged='Prozess-ID gehört nicht mehr zu dieser Koop-Sitzung.'
        UnknownCar='Dieses Startauto steht nicht zur Auswahl.'; CarFile='Autoauswahl-Datei konnte nicht gelesen werden. Bitte car-preferences.json prüfen.'
    }
}
function Get-CoopPersonalStateRoot { return Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop' }
function Get-CoopLanguage([string]$Requested='auto',[string]$StateRoot=(Get-CoopPersonalStateRoot),[string]$CultureName=[Globalization.CultureInfo]::CurrentUICulture.Name){
    if($Requested -in @('de','en')){return $Requested}
    try{
        $path=Join-Path $StateRoot 'language.json'
        if((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -le 4096){
            $saved=Get-Content -LiteralPath $path -Raw -Encoding utf8|ConvertFrom-Json
            if($saved.Language -in @('de','en')){return [string]$saved.Language}
        }
    }catch{}
    if($CultureName -match '^de($|-)'){return 'de'}
    return 'en'
}
function Save-CoopLanguage([ValidateSet('de','en')][string]$Language,[string]$StateRoot=(Get-CoopPersonalStateRoot)){
    [void][IO.Directory]::CreateDirectory($StateRoot)
    $temporary=Join-Path $StateRoot ([IO.Path]::GetRandomFileName())
    try{
        [IO.File]::WriteAllText($temporary,(@{Schema=1;Language=$Language}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temporary,(Join-Path $StateRoot 'language.json'),$true)
    }finally{if(Test-Path -LiteralPath $temporary){Remove-Item -LiteralPath $temporary}}
}
function Get-CoopText([string]$Key,[string]$Language=$script:CoopLanguage,[object[]]$Values=@()){
    if($Language -notin @('de','en')){$Language='en'}
    $value=$script:CoopStrings[$Language][$Key]
    if($null -eq $value){throw "Missing UI text: $Language/$Key"}
    if($Values.Count){return $value -f $Values}
    return $value
}
# Translate errors from the historical shared core without changing its patch/install logic.
function ConvertTo-CoopUserError([string]$Message,[string]$Language=$script:CoopLanguage){
    $keys=@{
        'Vollstaendiger Spielordner (enthaelt die Spiel-EXE)'='FolderPrompt'
        'THERUNBACKUP wird nicht verwendet.'='BackupProtected'; 'Im angegebenen Ordner fehlt die Spiel-EXE.'='MissingGame'
        'Bitte Spiel und Testserver zuerst schliessen.'='CloseGame'
        'Koop-Dateien fehlen oder wurden geaendert. Bitte Install-Coop.cmd ausfuehren.'='CoopMissing'
        'd3d11.dll ist noch aktiv. Bitte die Installation pruefen.'='D3dActive'
        'Prozess-ID gehoert nicht mehr zu dieser Koop-Sitzung.'='ProcessChanged'; 'Dieses Startauto steht nicht zur Auswahl.'='UnknownCar'
    }
    if($keys.ContainsKey($Message)){return Get-CoopText $keys[$Message] $Language}
    $prefix='LAN-Grunddatei fehlt/abweichend: '
    if($Message.StartsWith($prefix)){return Get-CoopText LanFile $Language @($Message.Substring($prefix.Length))}
    if($Message -match '^(Autoauswahl-Datei|Ungueltiges Autoauswahl-Profil|Doppeltes Autoauswahl-Profil|Zu viele Autoauswahl-Profile)'){return Get-CoopText CarFile $Language}
    return $Message
}
