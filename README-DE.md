# v0.7.5-TEST

[Changes / Änderungen](CHANGELOG.md)
[Updates and difficulty / Updates und Schwierigkeit](UPDATES-DIFFICULTY.md)

# The Run Story-Koop – Deutsch

[English](README-EN.md) · [Radmin einrichten](RADMIN-DE.md) · [Garage](GARAGE-DE.md)

Experimentelles Story-Koop-Testpaket. Jeder benötigt eine eigene unterstützte Spielinstallation und dasselbe Mod-Paket. Der Download enthält Patches, Starter und Mods, keine Spiel- oder Server-EXE. Versionsnummer, genaue Patchauswahl und Prüfgrenzen stehen in `GAMEPLAY-STATUS.json` und den beigefügten Versionshinweisen.

## Installieren und starten

1. ZIP vollständig entpacken. Spiel und Koop-Server schließen.
2. `Install.cmd` starten (`Install-Coop.cmd` bleibt der bisherige Installer). Den **Spielordner** angeben, in dem `Need For Speed The Run.exe` liegt. Falls verlangt, das eigene entpackte LAN-Grundpaket v1 vom 29.05.2024 angeben. Keine EXE-Dateien umbenennen, um Prüfungen zu umgehen.
3. Für verschiedene PCs [Radmin einrichten](RADMIN-DE.md).
4. `Launch-Coop.cmd` öffnen, Sprache wählen, Spielordner und Namen eintragen. `Launch-Coop.vbs` öffnet dieselbe Oberfläche ohne dauerhafte Startkonsole. `Koop-Starten.cmd` bleibt kompatibel.
5. Einer wählt **Hosten**, die anderen **Beitreten** und die Radmin-IPv4 des Hosts, ohne Port.
6. Der Host bestätigt im Starter mit Enter, sobald die Spielfenster aller Gäste offen sind. Dann startet der Server. Nur der Host wählt Story/Fortsetzen. Starter- und Garage-Fenster während der Sitzung offen lassen.

**Solo** im Launcher startet den Einzelspieler mit den installierten Mods. Nur die LAN-Option wird für diese Sitzung ausgeschaltet und danach zurückgestellt, wenn sie zwischenzeitlich nicht verändert wurde. Das Spiel speichert weiterhin normal.

PowerShell 7 wird benötigt; vorhandenes geeignetes PowerShell 7 wird verwendet. Es wird in diesem Stand noch nicht automatisch installiert. Hinweise: [Microsoft PowerShell für Windows](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows).

## Sprache und Einstellungen

Launcher und Garage bieten Deutsch/Englisch. Die persönliche Wahl wird auf diesem PC gespeichert; ohne Wahl gilt Deutsch bei deutscher Windows-UI, sonst Englisch. Name, Host-IP, Spielordner und lokale Fensteroptionen werden gemerkt. Das Auto wählt jeder selbst in seiner [Garage](GARAGE-DE.md).

Der Host kann das vorgesehene Serverlimit 1–4 auswählen. Vollständiger Vier-Spielerbetrieb ist noch nicht live bestätigt; bisherige lokale Tests verwenden höchstens zwei Spielclients. Die Schwierigkeit wird derzeit im Spiel gewählt; Launcher-Steuerung und automatische Übernahme vom Host sind noch offen. Es gibt keinen Pause-KI-aus-Schalter.

## Grenzen und Sicherungen

- Tankstellenauswahl weiterhin meiden: Vorschau, Laden und Rückkehr können hängen. Garage zwischen Missionen verwenden.
- Cutscenes, Host-/Gastkamera, QTEs und gescriptete Rennabschlüsse können weiter fehlerhaft sein. Ein bestandener einzelner Test bestätigt keine vollständige Kampagne.
- Der Installer sichert geänderte Installationsdateien. Koop-Starts sichern den aktuellen Spielstand; sie spielen keinen alten Stand zurück.
- Eigenes Spielfenster schließen oder `Stop-Coop.cmd` verwenden. `Restore-Installation.cmd` stellt gesicherte Installationsdateien wieder her, keine Spielstände. Musik-Rückstellung ist separat in `ADDONS.md` beschrieben.

**Übersetzungsstand:** Launcher, Garage und diese Anleitungen sind DE/EN. Der bestehende Installer, Wiederherstellung, Firewall-Helfer, Diagnosen und einige Addon-Hinweise enthalten noch deutsche Meldungen. Die englische Anleitung nennt die wichtigen Installer-Abfragen ausdrücklich. Keine vollständige Paketübersetzung behauptet.
