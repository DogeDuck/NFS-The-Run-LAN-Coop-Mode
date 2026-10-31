# Mit einem Freund über Radmin spielen

Diese Anleitung gehört zum experimentellen v0.3-Testpaket. Es ist noch nicht als
Gesamtpaket im Spiel geprüft. Beide benötigen dieselbe unterstützte Spiel- und Mod-Version. Das Paket verteilt Patches und Starter, keine Spieldateien.

## 1. Radmin verbinden

1. Auf beiden PCs Radmin VPN installieren und starten: https://www.radmin-vpn.com/.
2. Der Host erstellt über **Netzwerk → Netzwerk erstellen** ein privates Netzwerk mit
   Namen und Passwort. Ein vorhandenes gemeinsames Netzwerk kann weiterverwendet werden.
3. Der Freund wählt **Netzwerk beitreten** und trägt denselben Namen und das Passwort ein.
4. Prüft in Radmin, dass ihr euch gegenseitig online seht.
5. Der Host kopiert seine in Radmin angezeigte IPv4. Der Gast braucht die Radmin-IP
   des Hosts, nicht seine eigene Adresse und nicht die normale WLAN-Adresse.

Radmin-Anleitung: https://www.radmin-vpn.com/help/.
Netzwerkpasswort und persönliche Verbindungsdaten werden nicht im öffentlichen Mod-Paket gespeichert.

## 2. Gleichen Mod-Teststand installieren

1. Beide laden dasselbe als Testversion gekennzeichnete Paket aus dem GitHub-Release.
2. Spiel und Dedicated Server schließen.
3. Paket entpacken und **Install-Coop.cmd** starten. Den installierten Spielordner
   auswählen, in dem `Need For Speed The Run.exe` liegt.
4. Der Installer prüft die Dateiversionen und legt vor Änderungen Sicherungen an.
   Bei einer nicht unterstützten Version die angezeigte Meldung verwenden und den
   Installer nicht durch Umbenennen anderer EXE-Dateien umgehen.

## 3. Gemeinsam starten

1. Host öffnet **Koop-Starten.cmd**, wählt **Spiel hosten**, Spielordner und Spielernamen.
2. Gast öffnet **Koop-Starten.cmd**, wählt **Spiel beitreten** und trägt die kopierte
   Radmin-IP des Hosts ein. Ins IP-Feld kommt nur die Adresse, ohne `:25200`.
   Der Starter ergänzt den Spielport selbst.
3. Gast klickt **Verbinden**. Der Host bestätigt im Starterfenster mit Enter,
   sobald das Gast-Spielfenster geöffnet ist. Dann startet der Host-Starter den Server.
4. Die Starterfenster offen lassen. Nur der Host startet die Story bzw. das gemeinsam
   vereinbarte Testevent; der Gast wählt zunächst keine eigene Mission.
5. Zum Beenden **Stop-Coop.cmd** verwenden oder das eigene Spielfenster schließen.

Die bestehenden `Start-Host.cmd` und `Start-Guest.cmd` bleiben als Konsolenalternative
vorgesehen. Bei `Start-Guest.cmd` wird die Host-IP als Text abgefragt.

## Falls keine Verbindung zustande kommt

- Beide Radmin-Teilnehmer müssen online und im selben Netzwerk sein.
- Die IP muss vom Host stammen und aus Radmin kopiert sein.
- Der Host muss nach dem Gaststart den Serverstart im Starterfenster bestätigt haben.
- Die Windows-Firewall muss Radmin sowie Spiel/Server die Verbindung über das
  Radmin-Netz erlauben. Spiel und Server verwenden in diesem Starter den GamePort25200.
- Beide müssen exakt denselben Mod-Teststand verwenden. Spiel- oder Serverabstürze
  und Ladestatus angeben, statt wiederholt neue Server zu starten.

## Grenzen des Teststands

Der erste bestätigte Spawn-Fix ist auf Mission1.51 begrenzt. Einzelunfall mit
Weiterfahrt des anderen wurde einmal positiv getestet. Zeitablauf/Retry, gemeinsamer
Rennabschluss, weitere Missionen, Cutscenes und echte Internet-Verbindung sind noch
nicht vollständig verifiziert. In der zweiten getesteten Mission fehlten außerdem
Gegner und Verfolgung; nur gescriptete Cops waren sichtbar. Musik-Mod und separate Fahrzeugauswahl sind
nicht automatisch Bestandteil der bisher vorbereiteten Patches.
