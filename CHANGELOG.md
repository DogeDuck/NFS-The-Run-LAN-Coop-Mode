# v0.7.3 TEST / TESTVERSION

## English

- Eliminator: ignore duplicate/late checkpoint phase starts; a second teammate crossing cannot defeat the next rival or restart its timer.
- Filter native bots out of the teammate comparison. Existing NPC racers, team results and shared checkpoint time are retained.
- English/German launcher and garage, personal language choice, neutral Launch-Coop.cmd / Install.cmd aliases, bilingual Radmin instructions.
- Garage still opens with each client; vehicle/relay logic retained. Host/Join/Solo and saved host IP retained.
- Live: one complete2.6 run and duplicate-checkpoint test passed. Three/four-human phase cases only emulated; only two players tested live.
- QTE/cutscene synchronization, initial cutscene vehicle collisions,1.51 scripted ending/bridge, Chicago transition crash, gas stations and launcher difficulty remain open. Avoid gas stations; use the garage.
- Internal negative-ANT-time guard is NOT enabled in this release. No unsafe gas/timeout experiments. Installer and some helper messages remain partly German; see README-EN. PowerShell7 is still a prerequisite.

## Deutsch

- Eliminator: doppelte/verspaetete Checkpoint-Starts werden verworfen. Mitspieler besiegen am selben Checkpoint keinen weiteren Gegner und starten den Timer nicht neu.
- Bots aus Teamvergleich entfernt; KI-Gegner, Teamwertung und gemeinsame Checkpoint-Zeit bleiben erhalten.
- Launcher/Garage Deutsch und Englisch, persoenliche Sprachwahl, neutrale Starter und zweisprachige Radmin-Anleitung.
-2.6 einmal komplett und doppelter Checkpoint live bestanden;3/4 nur offline modelliert. Neue Oberflaeche noch kein Zwei-PC-Nachweis.
- QTE/Kameras, Cutscene-Kollisionen,1.51, Chicago-Absturz, Tankstellen und Launcher-Schwierigkeit bleiben offen. Tankstellen meiden, Garage verwenden. ANT-Zeit-Experiment nicht enthalten.
