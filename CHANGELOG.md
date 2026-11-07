# NFS: The Run LAN Coop Mode – v0.7.1 TEST

Experimentelle Story-Koop-Mod fuer zwei Spieler, lokal oder ueber Radmin VPN.
Beide brauchen eine eigene passende Spielinstallation und das unterstuetzte
LAN-Grundpaket v1 vom 29.05.2024. Enthalten sind Installer, Patches und Mods,
keine Spiel- oder Server-EXE.

## Neu zusammengefasst

- Pause-KI: Beim Oeffnen des Pausemenues wird das eigene Auto der nativen KI
  uebergeben; beim Schliessen wird die selbst aktivierte Uebernahme beendet.
  Im HOST live bestaetigt, noch kein umfassender Gast-/Cutscene-Test.
- Multiplayer-HUD: native Spieler-/Platzierungsliste statt des Story-Timers und
  der Autolog-Stage-Leader-Anzeige. Sichtbarer Wechsel live bestaetigt.
  Genauigkeit aller Sekundenabstaende und aller Rennanzeigen noch offen.
- Zusaetzlicher Startplatz fuer den zweiten menschlichen Fahrer auf den
  ausdruecklich unterstuetzten Events. Er soll keinen originalen NPC-Startplatz
  mehr belegen. Erster echter Gegner in Eliminator2.6 live korrekt gespawnt.
- Eigene Garage pro Client: oeffnet mit dem Spiel, ohne dauerhafte Konsole.
  Auto, Style-Pack und Variante waehlen; beim naechsten Fahrzeug-Spawn,
  Etappenwechsel oder Retry uebernommen. Beide Garage-Fenster offen lassen.
- Der Gast sendet seine Auswahl an das Garage-Fenster des Hosts (TCP25211).
  Der Fehler "ForeColor: Cannot convert null" bei der Bestaetigung ist behoben.
  Neuer Versand ueber zwei PCs/Radmin muss noch separat getestet werden.

## Bisherige Funktionen bleiben enthalten

- KI-Racer-Erweiterung; gescriptete Polizei/Verfolgungen sind separat zu pruefen.
- Erfasste Story-Startpositionen ab Stage2, Mitspieler versetzt dahinter;
  gezielte bisherige 1.51-Behandlung. Liste: SPAWN-EVENTS.json.
- Gemeinsame Checkpoint-Zeitboni fuer Zeitrennen.
- Gemeinsame normale Zielwertung (Mode0) und bisherige Story-Weiterwechsel.
  Das ist KEIN vollstaendiger gemeinsamer Eliminator-/Battle-Fix.
- Definitive Edition im Koop-Profil, Musik +25dB und vorhandene Freischaltungen.
  Details und Fremdmod-Credits: ADDONS.md und GARAGE.md.

## Installation und Verbindung

1. ZIP vollstaendig entpacken, Spiel und Server schliessen.
2. Auf beiden PCs Install-Coop.cmd starten. Den SpielORDNER angeben.
3. Beide PCs in dasselbe Radmin-VPN-Netzwerk bringen, siehe RADMIN-ANLEITUNG.md.
4. Koop-Starten.cmd: einer HOST, einer GAST. Der Gast traegt die Radmin-IPv4
   des Hosts ein. Die Host-Firewallhilfe umfasst auch die Garage (TCP25211).
5. Host startet den Server, sobald das Gast-Spielfenster offen ist. Nur der
   HOST startet das Rennen. Beide Garage-Fenster fuer gehaltene Autos offen lassen.
6. Stop-Coop.cmd beendet die eigene Sitzung. Restore-Installation.cmd stellt
   gesicherte Installationsdateien wieder her. Kein automatischer Save-Restore.

## Bekannte Fehler

- Eliminator: Wenn nur einer den echten NPC schlaegt, kann der andere weiterhin
  lokal verlieren und in KI-Steuerung wechseln. Gemeinsamer aktueller Gegner,
  Battle-Countdown, Zaehler und Ausgang sind NICHT geloest. Auch der Test, bei
  dem beide vor dem NPC bleiben, steht noch aus.
- Tankstellen meiden: Fahrzeugauswahl kann haengen oder abstuerzen. Die getestete
  Eintrittssperre wirkte nicht und ist nicht enthalten. Garage als Ersatz nutzen.
- Gast-Cutscenes, Kamera, Figuren und QTE-Eingaben sind nicht allgemein synchron.
  Die erste QTE laesst beide weiter, wenn einer sie schafft; kein neuer QTE-Fix.
- Bekannter Brueckenabsturz in1.51, einzelne Streaming-/Sound-/Spawnfehler und
  gescriptete Uebergaenge bleiben offen. Keine vollstaendige Kampagnenfreigabe.
- "Story-Auto" beendet beim Host das Halten des eigenen Autos; beim Gast ist
  diese Rueckgabe noch offen. Ein anderes Auto kann ausgewaehlt werden.

Offline202 Pruefungen vor dem Release-Paket bestanden; Paketpruefungen separat.
Live bestaetigte Teilfunktionen sind oben genannt. Nicht als fehlerfreie Version
oder als allgemeiner Fix fuer alle Rennarten verstehen.

Garage autostart hotfix: suppress only the PowerShell console (CreateNoWindow), keep the Garage window visible on every Host/Guest start. Game patches unchanged from v0.7.
