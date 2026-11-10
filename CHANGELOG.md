# v0.7.5 TEST

## Deutsch

- Korrektur nach Veröffentlichung0.7.4: GitHubs Versionsliste wird jetzt richtig als Array verarbeitet.0.7.4 wurde lokal nicht installiert; bitte direkt0.7.5 verwenden. Native Spielpatches sind identisch.


- Claudes bisherige RAM-Fixes fest eingebaut: Hostname bestimmt den Story-Spieler; zusätzliche Menschen bekommen in Chicago10.5 ein eigenes Skriptfahrzeug, der Story-Spieler das letzte; Chicago-Hubschrauber werden dem passenden zuletzt geladenen Abschnitt zugeordnet. Kein auslaufender Hilfsprozess mehr nötig.
- Chicago10.31: Gast übernimmt nicht Marcus Blackwells Startplatz. Die bestehenden NPC-, Teamabschluss-, Eliminator-Phasen-, gemeinsamen Zeit-, Garage- und DE/EN-Funktionen bleiben enthalten.
- Schwierigkeit im Launcher: Leicht, Normal, Schwer, Extrem. Der Server erzwingt diese Host-Wahl statt des zuletzt empfangenen Gastprofils. Offline gegen die nativen Speicherstellen geprüft; Wirkung auf das Fahrverhalten noch nicht live bestätigt.
- Launcher prüft GitHub im Hintergrund und kann veröffentlichte TEST-Updates automatisch installieren. Download und Paketdateien werden per SHA256 geprüft. Installation nur bei geschlossenem Spiel/Server; geänderte Moddateien und persönliche Einstellungen werden gesichert. Kein Spielstands-Restore. DEV-/GAS-/CANDIDATE-Pakete werden nicht automatisch angeboten.
- OOC/QTE nutzt wieder die ursprüngliche HUD-Policy, leeres STANDINGS wird ausgeblendet. Vollständige Gast-Szene, Kamera, Eingabe und QTE-Synchronisierung sind **weiterhin nicht repariert**: im letzten10.4-Test wanderte die aktive Szene nach Retry zum Host und blieb später auf dem Dach stehen.
- Ein neuer QTE-Kontext-Kandidat ist separat offline vorbereitet; er ist im normalen Paket **ausgeschaltet**. Kein pauschales Gast-Mute, kein vorgetäuschter QTE-Erfolg, kein ungeprüfter Kollisionspatch.
- Bekannte Grenzen: Cutscene-Kollisionen/anfängliche KI-Steuerung, Tankstellenwechsel (meiden, Garage verwenden),1.2Zug/1.51Brückenende, weitere QTEs und kompletter Vier-Spielerbetrieb offen.10.5-Ende ohne Gast-Mute braucht Gegenprobe. PowerShell7 bleibt Voraussetzung; automatische Mitinstallation noch offen. Installertexte teilweise Deutsch.

## English

- Correct the GitHub release-list array handling found after0.7.4 publication. Use0.7.5 directly; native gameplay patches are unchanged.


- Persist Claude's previously RAM-only fixes: select the story player by host nickname; spawn separate scripted vehicles for additional humans in Chicago10.5, with the story player entering last; resolve Chicago helicopter ownership to the correct most recently loaded section. No expiring helper process required.
- Chicago10.31 preserves Marcus Blackwell's rival slot. Existing NPC racers, team results, Battle checkpoint guards, shared checkpoint time, garage and bilingual UI remain included.
- Launcher difficulty: Easy, Normal, Hard, Extreme. The server applies the host's choice instead of accepting the last guest profile value. Native store paths verified offline; actual AI behavior still needs a live test.
- Background GitHub update check with optional automatic installation of published TEST releases. SHA256 checks cover the download and package contents. Game/server must be closed; changed mod files and personal settings are backed up. No game save restore. DEV/GAS/CANDIDATE releases are excluded.
- Preserve native OOC/QTE HUD policy and hide empty STANDINGS. Guest scene, camera, input and QTE synchronization remain **unfixed**. Latest10.4 test: Retry moved the complete scene to the host, then Jack stalled on the roof without a prompt.
- A separate experimental local QTE-context candidate is prepared offline and **disabled in this release**. No blanket guest mute, fake success or unverified collision patch.
- Known issues: cutscene car collisions/initial autopilot, gas station swaps (avoid; use garage),1.2train/1.51bridge ending, other QTEs and full four-player campaign. Retest10.5 ending without guest mute. PowerShell7 is required; automatic runtime installation remains pending. Some installer messages are German.
