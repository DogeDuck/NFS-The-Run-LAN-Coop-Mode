# Gemeinsam über Radmin spielen

[English](RADMIN-EN.md) · [Installation](README-DE.md)

1. Auf beiden PCs [Radmin VPN](https://www.radmin-vpn.com/) installieren und öffnen. Der Host erstellt ein privates Netzwerk; Gäste treten mit demselben Namen und Passwort bei. Ein bestehendes gemeinsames Netzwerk kann weiterverwendet werden. [Offizielle Hilfe](https://www.radmin-vpn.com/help/).
2. Prüfen, dass ihr euch in Radmin gegenseitig online seht. Der Host teilt seine **in Radmin angezeigte IPv4** mit den Gästen. Nicht die eigene Gast-IP oder die normale WLAN-IP verwenden. Persönliche Netzwerkpasswörter gehören nicht ins Mod-Paket.
3. Auf allen PCs dasselbe Mod-Testpaket installieren. `Launch-Coop.cmd` öffnen. Der Host wählt **Hosten**, Gäste wählen **Beitreten** und tragen die Host-IP ohne `:25200` ein.
4. Host und Gäste starten ihr Spiel über den Launcher. Der Host drückt in seiner Startkonsole erst Enter, wenn alle Gast-Spielfenster offen sind. Dann startet der Server. Nur der Host wählt Story/Fortsetzen.
5. Launcher- und Garage-Fenster während der Sitzung offen lassen. Jeder wählt sein eigenes Auto in der Garage, am besten zwischen Missionen. Tankstellen meiden.

## Wenn die Verbindung fehlt

- Radmin-Teilnehmer online, gleiches Netzwerk, korrekte Host-IP und gleicher Mod-Teststand prüfen.
- Der Host muss den Serverstart nach dem Öffnen der Gastspiele bestätigt haben.
- Das Spiel nutzt **UDP 25200**. Die Garage sendet die Gast-Auswahl an die Host-Garage über **TCP 25211** und verwendet automatisch dieselbe Host-IP.
- Windows-Firewall muss diese Verbindungen über das Radmin-Netz erlauben. Falls nötig kann der Host `Enable-HostFirewall.cmd -FriendVpnAddress GAST-RADMIN-IP` für genau die Radmin-IP des jeweiligen Gasts verwenden. Dabei gehört die **Gast-IP** in die Firewall-Regel, nicht die Host-IP. Dieser gezielte Schritt benötigt Administratorrechte; nur bei tatsächlichem Bedarf ausführen.
- Router-Portfreigaben sind für den gemeinsamen Radmin-Weg nicht erforderlich. Keine pauschalen Freigaben ergänzen.

Bei Absturz oder Ladehänger den betroffenen Client und den Zustand melden; nicht mehrere Server nebenher starten. Die genaue Versionsgrenze steht in [README-DE.md](README-DE.md) und `GAMEPLAY-STATUS.json`. Die Vorgabe 1–4 im Launcher ist noch kein bestätigter Vier-PC-Test.
