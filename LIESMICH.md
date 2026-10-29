# The Run Story-Coop – Prototyp 0.1

Für zwei Windows-PCs mit eigener Installation von Need for Speed: The Run.
Mit zwei Instanzen auf einem PC getestet; der Internettest mit zwei physischen
PCs steht noch aus.

## Bestätigte Koop-Regeln

- Beide Autos sind fahrbar und für den jeweils anderen sichtbar.
- Select setzt das eigene Auto normal auf die Straße zurück.
- Zeitablauf und Wrecked starten das Event für beide neu. Diese Regel ersetzt
  den bisher blockierenden Story-Checkpoint-Rewind.
- Beide sehen einen herunterzählenden Storytimer.

Offen: Zwischensequenzen unter der Map, vollständiger Missionsabschluss,
Kapitelwechsel und Langzeittest über das Internet. Bei zwei lokalen Fenstern
kann derselbe Controller beide Instanzen bedienen; auf zwei PCs benutzt jeder
seinen eigenen Controller.

## Vorbereitung auf beiden PCs

1. Das normale Spiel einmal bis in ein Rennen starten und wieder schließen.
2. Die passende LAN-Grundlage bereithalten: **NFSTR LANScript v1 vom 29.05.2024**.
   Dieses Paket enthält keine Spiel-EXE, keinen Server und keine ASI-/Loader-DLL.
   Falls die LAN-Grunddateien noch fehlen, das eigene Grundpaket separat
   entpacken. Der Installer fragt nach diesem Ordner.
3. Dieses Paket vollständig entpacken. `Install-Coop.cmd` starten und den
   tatsächlichen Spielordner angeben. Keine Backup-Spielinstallation verwenden.
   Der Installer sichert betroffene Originaldateien und prüft die Dateiversionen.
   Eine unbekannte EXE wird nicht blind gepatcht. Python ist nicht erforderlich.

Die vorbereiteten Spielversionen werden anhand ihrer Prüfsummen erkannt.
Ein anderes LAN-Paket oder eine abweichende Spielversion kann abgelehnt werden.
Spielassets müssen zwischen beiden PCs zusammenpassen; das ersetzt keinen
echten Verbindungstest.

## Über das Internet mit Radmin VPN

Auf beiden PCs Radmin VPN verwenden. Der Host erstellt ein privates Netzwerk
mit Namen und Passwort; der Kumpel tritt demselben Netzwerk bei. Anschließend
die Verbindung über die Ping-Funktion von Radmin prüfen. Namen und Passwort
direkt miteinander austauschen. [Offizielle Radmin-Anleitung](https://www.radmin-vpn.com/help/)

1. Host: `Start-Host.cmd` öffnen. Es startet das Host-Spiel und zeigt die
   aktuelle Radmin-IP. Das Starterfenster wartet zunächst.
2. Kumpel: `Start-Guest.cmd` öffnen und die Radmin-IP des Hosts eingeben.
3. Sobald beide Spielfenster offen sind, drückt der Host im wartenden
   Starterfenster Enter. Erst jetzt startet der dedizierte Server.
4. Wenn beide verbunden sind, wählt nur der Host **THE RUN → Fortsetzen**.
5. Jeder spielt auf seinem eigenen PC. Das Starterfenster offen lassen;
   beim Schließen des Host-Spiels beendet es auch seinen Server.

Der gemessene Spielport ist **UDP 25200**. Falls die Windows-Firewall das Hosten
blockiert, erlaubt `Enable-HostFirewall.ps1` gezielt nur diese Server-EXE und
die einzelne VPN-IP des Kumpels. Dieser optionale Schritt wird nicht automatisch
ausgeführt. Beispiel in einer PowerShell als Administrator:

```powershell
.\Enable-HostFirewall.ps1 -GameDirectory 'X:\Pfad\zum\Spiel' -FriendVpnAddress '26.1.2.3'
```

Die Firewall muss dafür nicht ausgeschaltet werden. Der Internettest und eine
eventuell nötige Freigabe werden erst geprüft, wenn beide PCs verbunden sind.

## Spielstände, Beenden und Rückbau

Vor jedem Start sichert der Starter den vorhandenen NFSTR-Spielstand unter
`%LOCALAPPDATA%\TheRunStoryCoop\Sessions`. Danach speichert das Spiel normal;
ein Kampagnen-Fortschritt über mehrere Kapitel ist noch nicht validiert.

`Stop-Coop.cmd` beendet nur die von diesem Starter aufgezeichnete Sitzung.
Bei einer umbelegten Prozess-ID verweigert es den Zugriff.

`Restore-Installation.cmd` stellt die Dateien aus dem Zustand **vor dieser
Paketinstallation** wieder her. Es verändert keine Spielstände. Falls bereits
vorher LAN-Mods installiert waren, ist der wiederhergestellte Zustand ebenfalls
diese vorherige LAN-Installation.

Die Installationssicherungen liegen unter
`%LOCALAPPDATA%\TheRunStoryCoop\InstallBackups`. Sicherungen bleiben erhalten.
Unbekannte nachträgliche Änderungen werden beim Rückbau nicht überschrieben.

## Quellen

Die LAN-Grundlage ist [NFSTR_LANOnlineHelper von Hypercycle / And799 / mRally2](https://github.com/hypernucle/NFSTR_LANOnlineHelper),
MIT-lizenziert. Das Paket enthält eine daraus abgeleitete Konfiguration und die
zugehörige MIT-Lizenz. Die zusätzlichen Koop-Patches und Starter werden mit
ihrem Quelltext geliefert. Keine Zugangsdaten oder privaten Netzwerkpasswörter
sind enthalten; es werden keine Nachrichten an Dritte versendet.
