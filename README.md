# NFS: The Run LAN Coop Mode

## v0.4 TEST — Definitive Edition + Musik

[Installer-Paket herunterladen](https://github.com/DogeDuck/NFS-The-Run-LAN-Coop-Mode/raw/refs/heads/main/downloads/TheRun-Coop-v0.4-TEST.zip)

ZIP entpacken, Spiel und Server schliessen, Install-Coop.cmd starten und den Spielordner angeben. Vorhandene passende LAN-Grunddateien werden weiterhin benoetigt; das Paket enthaelt keine Spiel-EXE und kein vollstaendiges Spiel.

Feste Bestandteile bei jeder Installation:
- Bisheriger Zwei-Spieler-Story-Coop mit Checkpoint-/Timer- und gezielten Spawn-Aenderungen.
- Definitive Edition, selbst aus MIT-Quellcode gebaut: Motor-Audio-/Partikelfixes, 144-FPS-Ziel und Cutscene/QTE-Clamp. Zusaetzliche Schwierigkeits-, Verkehrs-, Fahrzeug- und Renderaenderungen sind im Coop-Profil deaktiviert.
- Musik +25dB, Effekte -2dB, Sprache original. Wiederholtes Installieren erhoeht den Pegel nicht weiter.

SHA256: `9ab143e26171011cbd22444ec0e4df58d4cf63b4fbac1824780af74ab4a3e7d7`

**Experimentelle Testversion.** Installer-Vorpruefung, Paketpruefsummen und Win32-ASI geprueft. Das Zusammenspiel von Definitive Edition und LAN-Coop ist noch nicht ingame verifiziert.

### Bekannte offene Fehler und naechste Arbeit

Die Bruecke/Straßensperre in Mission1.51 kann beide Clients zum Absturz bringen; alternativ fehlen Sprung-Cutscene und Folgestrecke. Dies ist NICHT behoben. Fehlende KI-Racer und ein gemeinsamer Rennabschluss (ein Mensch gewinnt fuer das ganze Team, danach natives Continue The Run) sind die naechsten Entwicklungsziele und noch NICHT in dieser Version umgesetzt.

Die lokalen experimentellen SEC05-Vorlade-Hooks sind NICHT Bestandteil dieses Pakets. Ausgelieferte Spieldeltas behalten den bisherigen Entwicklungsstand.

### Radmin

Beide PCs ins gleiche Radmin-VPN-Netz verbinden. HOST startet Start-Host.cmd; GAST startet Start-Guest.cmd und gibt die Radmin-IP des Hosts ein. Ausfuehrliche Anleitung liegt im ZIP als RADMIN-ANLEITUNG.md bei. Beide Spieler benoetigen ihre eigene kompatible Spielinstallation und denselben Modstand.

### Wiederherstellung

Restore-Installation.cmd stellt die vom Coop-Installer gesicherten Dateien einschliesslich DE-ASI/INI wieder her. Der Audiomix wird separat ueber `addons/music25/NFS-Audio-Patch.ps1 -GamePath "SPIELORDNER" -Mode Restore` zurueckgesetzt. Siehe ADDONS.md im ZIP.

### Quellen

Definitive Edition: https://github.com/BadassBaboon/NFS-TheRun-DE, Commit048ab8fadbe3938f5651e9dabf09b3db64a6dc7d, MIT-Lizenz im Paket. Vorhandener lokaler Musikpatch in das Installationspaket integriert. Die Coop-LAN-Basis bleibt erforderlich; kein beliebiger AnyCoop-Downloader wird installiert.
