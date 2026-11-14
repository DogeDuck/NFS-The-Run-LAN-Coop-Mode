# Installation — v0.7.8-TEST

1. Spiel und Server schließen. Auf jedem PC das eigene unterstützte Originalspiel und die benötigte LAN-Basismod installieren.
2. TheRun-Coop-v0.7.8-TEST.zip vollständig entpacken. Den ganzen Ordner behalten, nicht nur den Installer.
3. Install.cmd starten und den Spielordner wählen. Der Installer prüft bekannte Dateihashes, sichert geänderte Installationsdateien und erhält persönliche INIs. PowerShell7 wird bei Bedarf bereitgestellt. Spielstände werden nie zurückgespielt.
4. Launch-Coop.cmd oder Launch-Coop.vbs starten. Host / Beitreten / Solo wählen; Gäste geben die VPN-IPv4 des Hosts ein. Alle verwenden dieselbe Paketversion: [Radmin-Anleitung](RADMIN-DE.md).
5. Nur der Host startet die Story. Alle Garage-Fenster geöffnet lassen, damit die Autowahl erhalten bleibt. Der Host-QTE-Helfer startet automatisch. Falls nötig freundbezogene Regeln für TCP25211/25212 und UDP25200/25214 über Enable-HostFirewall.ps1 auf den betreffenden PCs anlegen.

[Funktionen / Vorschau](README.md) · [Sitzung, Garage und Diagnose](SESSION-DE.md) · [Änderungen und bekannte Fehler](CHANGELOG.md)

Testversion: Gesamtpaket, QTE-Netztransport, neue Cutscene-/Lichtfunktionen und vollständige Vier-PC-Unterstützung sind noch nicht live bestätigt. Vorher Spielstand sichern. Der alte feste25-dB-Mix wird nicht angeboten.
