#requires -Version 7.0
# Presentation boundary only. Garage-Core and the existing relay protocol stay unchanged.
. (Join-Path $PSScriptRoot 'Coop-Language.ps1')
$script:GarageText=@{
    'The Run Koop – Garage'='The Run Co-op – Garage'
    'Suche dein Spiel ...'='Looking for your game ...'; 'Warte auf dein Spiel ...'='Waiting for your game ...'
    'Auto suchen'='Search cars'; 'Paket'='Pack'; 'Variante / Lack'='Variant / paint'
    'Fürs nächste Rennen übernehmen'='Apply for the next race'; 'Story-Auto'='Story car'
    'Vorschaubild...'='Choose image...'; 'Foto aus Spiel'='Capture game'
    'Du wählst nur dein eigenes Auto. Es kommt beim nächsten Etappenstart und bleibt auch nach Retry, solange dieses Fenster offen ist. Der Host muss sein Garage-Fenster ebenfalls offen haben.'='Choose only your own car. It appears at the next stage start and stays selected after Retry while this window is open. The host must also keep their garage open.'
    'Lade Foto von Wikimedia Commons ...'='Loading a photo from Wikimedia Commons ...'
    'Kein Foto gefunden – "Foto aus Spiel" oder eigenes Bild hineinziehen.'='No photo found. Use "Capture game" or drag your own image here.'
    'Kein Vorschaubild – "Foto aus Spiel" klicken oder ein Bild ins Fenster ziehen.'='No preview. Click "Capture game" or drag an image into this window.'
    'Serie'='Stock'; 'Einzeln'='Single'; 'Style-Pack 1'='Style Pack 1'; 'Style-Pack 2'='Style Pack 2'; 'Style-Pack 3'='Style Pack 3'
    'Gast'='Guest'; ' · wird gehalten'=' · selection held'; ' · aktuell '=' · current '
    'Dein Spieler ist noch nicht im Rennen.'='Your player is not in the race yet.'
    'Auto wird nicht mehr gehalten – die Story wählt wieder selbst.'='Your car is no longer held. The story chooses it again.'
    'Story-Auto: nur der Host kann das Halten beenden (oder einfach ein anderes Auto wählen).'='Story car: only the host can stop holding the selection. Guests can choose another car instead.'
    'Host-Adresse unbekannt.'='Host address is unknown.'; 'Kein Spiel gefunden.'='No game found.'
    'Vorschaubild aus dem Spiel gespeichert.'='Game preview saved.'; 'Eigenes Vorschaubild gespeichert.'='Your preview image was saved.'
    'Garage-Fenster.ps1 fehlt.'='Garage-Fenster.ps1 is missing.'
    'Garage-Katalog ist zu gross.'='The garage catalogue is too large.'; 'Ungueltiger Garage-Eintrag.'='Invalid garage catalogue entry.'
    'Ungueltige oder doppelte Fahrzeug-Kennung.'='Invalid or duplicate vehicle key.'; 'Ungueltiger Datenbankname.'='Invalid database entry name.'
    'Module des Spiels nicht lesbar.'='Could not read the game modules.'; 'Das ist kein The-Run-Prozess.'='This is not a The Run process.'
    'Kein Zugriff auf das Spiel (gleiche Rechte wie das Spiel noetig).'='Cannot access the game. Run the garage with the same permissions as the game.'
    'Unerwarteter Spielprozess (nicht 32-Bit).'='Unexpected game process: it is not 32-bit.'
    'LAN-Helper ist in diesem Spiel nicht geladen.'='The LAN helper is not loaded in this game.'
    'Unbekannte LAN-Helper-Version; Garage nicht freigegeben.'='Unsupported LAN helper version. The garage cannot use it.'
    'Aktuelle Vorgabe nicht lesbar.'='Could not read the current car selection.'
    'Kennung steht nicht im Garage-Katalog.'='This vehicle key is not in the garage catalogue.'
    'Schreiben fehlgeschlagen.'='Could not write the car selection.'; 'Kontrolle nach dem Schreiben fehlgeschlagen.'='Car selection verification failed after writing.'
    'LOCALAPPDATA fehlt.'='LOCALAPPDATA is missing.'; 'Ungueltiger Bildname.'='Invalid preview image name.'
    'Nur PNG, JPG oder BMP.'='Use a PNG, JPG or BMP image.'; 'Bild ist zu gross.'='The image is too large (maximum 20 MB).'
    'Spielfenster nicht gefunden.'='Game window not found.'; 'Spielfenster ist minimiert.'='The game window is minimized.'
    'Fenstergroesse nicht lesbar.'='Could not read the game window size.'; 'Spielfenster zu klein.'='The game window is too small.'
    'Das ist kein The-Run-Server.'='This is not a The Run server.'
    'Unbekannte Server-Version; Server-Modus nicht freigegeben.'='Unsupported server version. The garage cannot use it.'
    'Kein Zugriff auf den Server.'='Cannot access the server.'; 'Unerwarteter Serverprozess (nicht 32-Bit).'='Unexpected server process: it is not 32-bit.'
    'Server-Code nicht lesbar.'='Could not read the server code.'
    'Server-Autovorgabe ist umgeleitet (ForceServerPlayersCarHash aktiv?). Bitte im Helper auf 0 setzen.'='The server car getter is redirected. Check whether ForceServerPlayersCarHash is enabled; the garage requires it to be 0.'
    'Unerwarteter Spieler-Offset.'='Unexpected player offset.'
    'Spieler-Auto hat sich inzwischen geaendert; bitte neu suchen.'='The player car changed in the meantime. Wait for the player list to refresh and try again.'
    'Kein Zugriff auf das Spiel.'='Cannot access the game.'
    'Host-Garage nicht erreichbar (Fenster beim Host offen? Firewall TCP 25211?).'='Cannot reach the host garage. Is its window open? Does the firewall allow TCP 25211?'
    'ungueltig'='invalid request'; 'fremder Slot'='player slot is not allowed'
}
$script:GaragePatterns=@(
    @('^Kennung: (.+)$','Key: {0}'),
    @('^Spaß \(experimentell, nicht offiziell fahrbar\) – Liste aus: (.+)$','Fun vehicle (experimental, not officially driveable). Source: {0}'),
    @('^Tier (.+) von 6 \(Serienversion laut NFS-Wiki\)$','Tier {0} of 6 (stock version, according to the NFS Wiki)'),
    @('^Dein Auto \((.+)\) – warte, bis du im Rennen bist \.\.\.$','Your car ({0}) – waiting for you to enter a race ...'),
    @('^Dein Auto · Spieler (\d+) \((.+)\)(.*)$','Your car · Player {0} ({1}){2}'),
    @('^Spieler (\d+) ist gerade nicht im Rennen\.$','Player {0} is not in the race right now.'),
    @('^Übernommen: (.+) – kommt beim nächsten Etappenstart und wird gehalten \(Fenster offen lassen\)\.$','Applied: {0}. Appears at the next stage start and stays selected while this window is open.'),
    @('^Gast \(Spieler (\d+)\) hat ein Auto gewählt\.$','Guest (player {0}) selected a car.'),
    @('^Auto für Spieler (.+) erneut gesetzt \(Retry/Checkpoint\)\.$','Car selection restored for player(s) {0} (Retry/checkpoint).'),
    @('^Unerwarteter Altwert (0x[0-9A-F]+); nichts geschrieben\.$','Unexpected previous value {0}; nothing was written.'),
    @('^Speicher nicht lesbar bei (0x[0-9A-F]+)\.$','Could not read memory at {0}.'),
    @('^(.+) mehrfach geladen\.$','{0} is loaded more than once.')
)
function Get-GarageUiText([string]$Text,[string]$Language=$script:CoopLanguage){
    if($Language -ne 'en'){return $Text}
    if($script:GarageText.ContainsKey($Text)){return $script:GarageText[$Text]}
    foreach($prefix in @('Gast-Anfragen nicht moeglich: ','Host lehnt ab: ')){
        if($Text.StartsWith($prefix)){
            $label=if($prefix -eq 'Host lehnt ab: '){'Host rejected the request: '}else{'Could not accept guest requests: '}
            return $label+(Get-GarageUiText $Text.Substring($prefix.Length) $Language)
        }
    }
    foreach($pattern in $script:GaragePatterns){
        $match=[regex]::Match($Text,$pattern[0])
        if($match.Success){
            $values=@(for($index=1;$index -lt $match.Groups.Count;$index++){
                $part=$match.Groups[$index].Value
                $part=$part.Replace('Gast','Guest').Replace(' · aktuell ',' · current ').Replace(' · wird gehalten',' · selection held')
                $part=$part.Replace(' · Serie ',' · Stock ').Replace(' · Style-Pack ',' · Style Pack ').Replace(' · Einzeln ',' · Single ')
                $part
            })
            return $pattern[1] -f $values
        }
    }
    if($Text.StartsWith('★ Spaß · ')){return '★ Fun · '+$Text.Substring('★ Spaß · '.Length)}
    if($Text.StartsWith('Foto: ')){return 'Photo: '+$Text.Substring(6)}
    if($Text.StartsWith('Bild: ')){return 'Image: '+$Text.Substring(6)}
    return ConvertTo-CoopUserError $Text $Language
}
