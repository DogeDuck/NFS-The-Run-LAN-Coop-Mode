# NFS: The Run LAN Coop Mode – v0.5 TEST

Experimentelle Story-Koop-Mod fuer zwei Spieler. Beide benoetigen eine eigene
passende Spielinstallation und das unterstuetzte LAN-Grundpaket v1 vom 29.05.2024.
Der Download enthaelt Patches und Mod-Dateien, keine Spiel- oder Server-EXE.

## Neu in dieser Version

- Native KI-Racer werden im Story-LAN wieder angelegt. Der zusaetzliche Mensch
  soll keinen urspruenglichen Gegner verdraengen. Der Fix prueft Startplatzkapazitaet
  und Belegung; bei unzureichendem Platz greift die Erweiterung nicht.
- Story-Startplaetze fuer 38 ausdruecklich erfasste Rennen ab Stage 2:
  erster verarbeiteter menschlicher Fahrer am vorgesehenen Einzelspieler-Start,
  zweiter Fahrer acht Meter hinter diesem Punkt entlang der Fahrtrichtung.
  Beide behalten eigene Fahrzeuge und native Besitzerzuordnung. Die genaue
  Reihenfolge wird von der Engine bestimmt, nicht fest von HOST/GAST.
- Die neue Spawnlogik greift nicht in Stage 1. Die bisherige gezielte
  1.51-Spawnbehandlung des Client-Patches bleibt unveraendert enthalten.
- Definitive Edition im eingeschraenkten Koop-Profil sowie Musik +25 dB bleiben
  enthalten und werden vom Installer angewendet. Details: ADDONS.md.

## Was wurde tatsaechlich getestet?

Spieltest: In Rennen 3.5 stehen beide Autos nach vollstaendigem Retry am
Rennanfang auf der Strasse und sind fahrbar. Serverzaehler bestaetigen die
Startplatzwahl fuer beide und jeweils eine Matrixkorrektur. KI-Racer wurden
zuvor in Desert Hills sowie Las Vegas mit der urspruenglichen Gegneranzahl
bestaetigt. Die anderen 37 Spawn-Eintraege wurden noch nicht im Spiel geprueft.

Die kombinierte Installerversion wurde offline geprueft, nicht als gesamte
Kampagne oder auf zwei PCs im Spiel getestet. SPAWN-EVENTS.json enthaelt die
ausdrueckliche Rennliste. GAMEPLAY-STATUS.json trennt Spielbelege und Grenzen.

## Installation / Update auf beiden PCs

1. ZIP vollstaendig entpacken; Spiel und Testserver schliessen.
2. Install-Coop.cmd starten und den SPIELORDNER angeben, nicht die EXE-Datei.
   Updates von v0.3/v0.4 sowie den unterstuetzten Grundfassungen werden erkannt.
3. RADMIN-ANLEITUNG.md befolgen: beide in dasselbe Radmin-VPN-Netzwerk.
4. Koop-Starten.cmd: einer HOST, der andere GAST. Der Gast traegt die
   Radmin-IPv4 des Hosts im IP-Feld ein.
5. Im Host-Starter erst Enter druecken, wenn das Gast-Spielfenster offen ist.
   Nur der HOST startet das Rennen. Starterfenster offen lassen.

Der Installer sichert geaenderte Installationsdateien. Die Starter sichern vor
dem Start den aktuellen Spielstand; sie schreiben keinen alten Stand zurueck.
Stop-Coop.cmd beendet die eigene Sitzung. Restore-Installation.cmd stellt
Installationsdateien wieder her; fuer die Musik gilt zusaetzlich ADDONS.md.

## Bekannte Grenzen – bitte vor dem Test lesen

- Tankstellenwechsel ist NICHT repariert: fehlende Vorschau, Endlosladen und
  Softlock nach Auswahl oder Zurueck. Tankstellen vorerst meiden.
- Pause-Menue mit KI-Uebernahme ist noch nicht enthalten.
- Der neuere Teamwertungs-Prototyp und gemeinsame Overtaken-HUD sind nicht
  Bestandteil dieser Version. Sieg/Verlust und Story-Fortschritt koennen weiter
  abweichen oder ein Rennen wiederholen.
- Brueckenabsturz in 1.51 weiterhin offen. Cutscene-Figuren, Gastkamera,
  Fahrzeugton und Steuerungsuebergaben koennen fehlerhaft sein.
- Kein vollstaendiger Verfolgungs-/Polizei-Fix: gescriptete Cops und Weltstreaming
  sind unabhaengig von der KI-Racer-Erweiterung.
- Spaetere Resets, andere Rennstarts und Uebergaenge brauchen weitere Tests.

Keine Tankstellen-Diagnose, kein experimenteller Garagen-Routing-Hook und keine
automatischen Prozessaufnahmen werden durch dieses Update gestartet.
