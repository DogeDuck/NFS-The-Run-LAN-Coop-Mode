# Koop-Garage (Auto waehrend der Sitzung wechseln)

Jeder Spieler waehlt sein eigenes Auto. Die Kopfzeile zeigt die vom eigenen Spiel gelesene Spieler-Nummer und Host/Gast. Beide Garage-Fenster offen lassen: Der Host nimmt die Auswahl des Gasts ueber TCP 25211 entgegen und haelt sie am Server auch nach Retry fest.

1. Spiel mit dem Koop-Starter starten; das Garage-Fenster oeffnet automatisch.
   Die Konsole bleibt verborgen. Manuell oeffnet Garage-Fenster.cmd die Oberflaeche ueber den beigefuegten Windows-GUI-Starter; PowerShell 7 wird weiterhin benoetigt.
2. Ein Rennen laden und die eigene Spieler-Nummer in der Kopfzeile pruefen.
3. Links ein Auto waehlen (sortiert nach Tier 1-6 wie im Spiel, Spass-Autos am Ende), dann das Paket (Serie, Style-Pack 1-3) und die Variante (1-8).
4. "Fuers naechste Rennen uebernehmen" klicken. Das neue Auto kommt beim naechsten Fahrzeug-Spawn (naechstes Rennen oder Retry).
5. "Story-Auto" beendet beim Host das Halten des eigenen Autos. Beim Gast ist diese Rueckgabe noch nicht implementiert; dort ein anderes Auto waehlen.

Sofern verfuegbar, laedt das Fenster Modellfotos von Wikimedia Commons mit Urheber und Lizenz. Die Fotos zeigen nicht notwendigerweise die gewaehlte Spielvariante. Alternativ ein eigenes Bild hineinziehen oder "Foto aus Spiel" verwenden (nur das Spielfenster).
Die Bilder liegen lokal unter %LOCALAPPDATA%\TheRunStoryCoop\previews und werden nicht weitergegeben.

Das Hostfenster schreibt die gepruefte Fahrzeug-Kennung in den Story-Spielerdatensatz des Servers. Prozess, Serverversion und Katalogwert werden geprueft. Spielstand, INI und EXE werden von der Garage nicht geaendert.

Live bestaetigt am 06./07.11.: getrennte Autos, Style-Packs, Etappenwechsel und Retry mit Halten-Timer. Die neue automatische Spielerzuordnung und der Gast-zu-Host-Versand muessen noch gemeinsam getestet werden.
Beim lokalen Zwei-Fenster-Test startet der Gast mit -RelayOnly und benutzt ebenfalls den Host-Versand. Damit wird keine Verbindung ueber Radmin oder eine fremde Firewall bewiesen.
Am sichersten zwischen Missionen wechseln. Die defekte Tankstellenauswahl nicht benutzen.

## Spass-Autos (mit Stern markiert)
36 nicht offiziell fahrbare Fahrzeuge: Polizei, Taxi, Bus, Traktor, Lkw, Wohnmobil und Testautos.
Sie sind experimentell. Physik, Kamera und Story koennen sich seltsam verhalten, und manche spawnen eventuell gar nicht.
Credit: Die Auswahl dieser Fahrzeuge stammt aus "Need For Speed The Run Car Changer" von Enksx1 / 379Felipe
(https://nfsmods.xyz/mod/282, 2017). Danke! Uebernommen wurden nur die Fahrzeug-Kennungen, kein Programmcode.

Tier-Einteilung (Serienversion je Modell): Need for Speed Wiki, https://nfs.fandom.com/wiki/Need_for_Speed:_The_Run/Cars
