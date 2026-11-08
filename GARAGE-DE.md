# Garage – eigenes Auto wählen

[English](GARAGE-EN.md) · [Start und Installation](README-DE.md)

1. Das Garage-Fenster öffnet sich beim Koop-Start automatisch. Manuell: `Launch-Garage.cmd` oder der kompatible deutsche Name `Garage-Fenster.cmd`.
2. Deutsch/English oben rechts wählen. Die Sprache bleibt persönlich und gilt auch für den Launcher beim nächsten Öffnen.
3. Ein Rennen laden. Die Kopfzeile zeigt deine eigene Spieler-Nummer und Host/Gast. Beide Garage-Fenster offen lassen: Der Host nimmt Gast-Auswahlen über TCP 25211 entgegen.
4. Auto suchen und links auswählen, dann Paket und Variante/Lack. **Fürs nächste Rennen übernehmen** klicken. Das Auto kommt beim nächsten Fahrzeug-Spawn/Etappenstart oder Retry, nicht sofort mitten im Rennen. Die Auswahl wird gehalten, solange die Host-Garage offen bleibt.
5. **Story-Auto** beendet beim Host das Halten des eigenen Autos. Beim Gast ist diese Rückgabe noch nicht implementiert; dort ein anderes Auto wählen.

Wähle am besten zwischen Missionen. Gas stations/Tankstellen sind weiterhin fehlerhaft und sollen gemieden werden. Die Garage verändert keine Spielstands-, INI- oder EXE-Datei; sie setzt die geprüfte Autoauswahl für den jeweiligen Spieler am laufenden Server.

Modellfotos werden bei Verfügbarkeit von Wikimedia Commons geladen und mit Urheber/Lizenz angezeigt. Sie zeigen nicht unbedingt die gewählte Spielvariante. Alternativ eigenes PNG/JPG/BMP hineinziehen oder **Foto aus Spiel** verwenden; dieser Knopf nimmt nur das Spielfenster auf. Bilder bleiben lokal in `%LOCALAPPDATA%\TheRunStoryCoop\previews`.

Stern-Markierung bedeutet experimentelles Spaß-Auto: Polizei, Bus, Taxi, Lkw und weitere Fahrzeuge sind nicht offiziell fahrbar. Physik, Kamera, Spawn und Story können fehlschlagen. Quelle der Fahrzeugauswahl: [Car Changer von Enksx1 / 379Felipe](https://nfsmods.xyz/mod/282); nur Fahrzeugkennungen übernommen. Tier-Zuordnung: [NFS Wiki](https://nfs.fandom.com/wiki/Need_for_Speed:_The_Run/Cars).

Getrennte Autos, Style-Packs und Halten nach Etappenwechsel/Retry wurden lokal geprüft. Ein lokaler Gast nutzt ebenfalls das Relay. Das beweist keine Erreichbarkeit durch die Firewall auf einem anderen PC und keinen vollständigen Vier-Spielerbetrieb.
