# Installation mit Setup

[**TheRun-Coop-v0.7.10-TEST-Setup.exe**](https://github.com/DogeDuck/NFS-The-Run-LAN-Coop-Mode/releases/download/v0.7.10-TEST/TheRun-Coop-v0.7.10-TEST-Setup.exe) · ZIP: **Setup.vbs**

# v0.7.10-TEST — Guided setup / Geführte Installation

DE: OneDrive-Sicherung korrigiert: Cloud-Dateien werden kopiert und geprüft, echte Symlinks/Junctions weiterhin abgelehnt. Neues eigenständiges Setup-EXE mit DE/EN-Oberfläche. Spielordnerwahl,
automatischer Bezug der geprüften originalen LAN-Basis (ca.16MB), ZIP/7z-/Ordnerimport,
PowerShell7-Bereitstellung, Fortschritt und vollständige Fehlerdetails. Jede
Setup-Installation baut Client/Server und unsere Moddateien frisch aus der bekannten
LAN-Basis auf und schreibt sie erneut. Die technische LAN-Konfiguration wird neu
angelegt; ihre alte Fassung wird gesichert. Launcher-/Garageprofile, persönliche
Grafik-INI und Spielstände bleiben erhalten. Saves werden vorher frisch gesichert,
nachher auf Unverändertheit geprüft und niemals zurückgespielt.

Desktop-Verknüpfung und Launcher öffnen ohne dauerhaftes leeres Konsolenfenster.
Reparatur zeigt verständliche Ergebnisse statt JSON. Veraltete Startauto/ViewCars-
Anweisungen entfernt. Die bisherige Host-Enter-Abfrage bleibt bis zum Lobby-Umbau.

Native Gameplay-Patches unverändert aus0.7.8: QTE/Cutscene/Licht-Experimente behalten
ihre bisherigen Grenzen. Zwei lokale Clients zeigten im aktuellen Test das Menü;
Schwarzbild bei zwei PCs (auch mit Yasin als Host) weiter ungeklärt. Neuinstallation
ist kein behaupteter Fix dafür. Kein neuer vollständiger Kampagnen-/Vier-PC-Nachweis.

EN: Fixed OneDrive backup: cloud placeholders are copied and checked, actual symbolic links/junctions remain rejected. New standalone bilingual Setup EXE: choose the game folder, download the verified
original LAN base (about16MB) or import it, prepare PowerShell7, see progress and
full error details. Every setup reconstructs and rewrites managed mod files from
the known original LAN base. The technical LAN configuration is regenerated and
its old copy backed up. Launcher/garage profiles, personal graphics INI and saves
are preserved. Current saves are backed up and checked, never restored.

Console-free launcher entry, desktop shortcut, readable repair results and retired
legacy starting-car instructions. Host Enter prompt remains until the lobby redesign.
Native patches unchanged from0.7.8. Remote black-screen issue remains unresolved;
fresh setup is not claimed to fix it. Existing experimental gameplay limits apply.

Download TheRun-Coop-v0.7.10-TEST-Setup.exe for the guided installer. The ZIP remains
available for portable/manual use. No complete game/server executables are included;
the original LAN base is fetched separately and checked against pinned SHA256.


# Installation — v0.7.10-TEST

1. Spiel und Server schließen. Auf jedem PC das eigene unterstützte Originalspiel und die benötigte LAN-Basismod installieren.
2. TheRun-Coop-v0.7.10-TEST.zip vollständig entpacken. Den ganzen Ordner behalten, nicht nur den Installer.
3. Install.cmd starten und den Spielordner wählen. Der Installer prüft bekannte Dateihashes, sichert geänderte Installationsdateien und erhält persönliche INIs. PowerShell7 wird bei Bedarf bereitgestellt. Spielstände werden nie zurückgespielt.
4. Launch-Coop.cmd oder Launch-Coop.vbs starten. Host / Beitreten / Solo wählen; Gäste geben die VPN-IPv4 des Hosts ein. Alle verwenden dieselbe Paketversion: [Radmin-Anleitung](RADMIN-DE.md).
5. Nur der Host startet die Story. Alle Garage-Fenster geöffnet lassen, damit die Autowahl erhalten bleibt. Der Host-QTE-Helfer startet automatisch. Falls nötig freundbezogene Regeln für TCP25211/25212 und UDP25200/25214 über Enable-HostFirewall.ps1 auf den betreffenden PCs anlegen.

[Funktionen / Vorschau](README.md) · [Sitzung, Garage und Diagnose](SESSION-DE.md) · [Änderungen und bekannte Fehler](CHANGELOG.md)

Testversion: Gesamtpaket, QTE-Netztransport, neue Cutscene-/Lichtfunktionen und vollständige Vier-PC-Unterstützung sind noch nicht live bestätigt. Vorher Spielstand sichern. Der alte feste25-dB-Mix wird nicht angeboten.
