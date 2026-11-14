# Local actors + HOST milestones / Lokale Akteure + HOST-Szenenfortschritt

Deutsch: Interner Testkandidat, NICHT installiert/veröffentlicht, kein bestätigter
QTE-Fix. (1) BasicControllable-Verknüpfungen wählen im LAN-Story-QTE die eigene
Figur wie die native Cinebot-Kamera. (2) Der anhand des ausdrücklich gewählten
Hostnamens verifizierte HOST löst zwei echte 10.4-Szenen-Meilensteine einmal aus:
kickandrun.OnStarted und herostealscar.OnFinished. Gastmeldungen zählen dort nicht
erneut. ANIMATIONS-MEILENSTEINE, KEINE Ladebestätigungen. Der alte READY-ACTOR-
Wartekandidat ist ZURÜCKGEZOGEN. Kein Warten auf alle Menschen an diesen Knoten.
Alle anderen EventSync-/Lade-Nachrichten bleiben nativ. R2: Umordnen der Menschenliste
oder Abmelden eines Gasts darf erledigte Schritte nicht erneut freigeben.
Retry/Etappenwechsel und
echte Quell-Subwelt-Ladevorgänge setzen die passende Instanz zurück. Hostname fehlt
oder passt nicht: konservativ originales Verhalten.

Native-byte-Test: Originalserver lässt eine verspätete zweite Meldung den bereits
geladenen Abschnitt entladen/neu laden. Host-Meilenstein zählt einmal. Die lokale falsche
Akteurzuordnung und ihre Korrektur sind ebenfalls mit echten Spielanweisungen
emuliert. Das ersetzt keinen Test von Welt, Kamera, Eingabe und kompletter QTE.
Host-only-Eingabe ist NICHT vollständig implementiert; Guest-Fail-NIS bleibt nativ.
Kein Start-Replay, allgemeines Gast-Mute, neuer
Frame-Hook, Polling oder Timeout. Keine weiteren experimentellen Fixes enthalten.

English: Internal test candidate, NOT installed/published; whole-QTE success is
unverified. Local human actor-link selection plus HOST-authoritative, once-per-
generation handling of kickandrun.OnStarted / herostealscar.OnFinished in 10.4.
These are ANIMATION milestones, NOT readiness. The former READY-ACTOR barrier is
WITHDRAWN. No waiting for every human at these nodes. Host is verified by explicit
name, never player0/list order. Retry/new mission and real source subworld reload
rearm the state. All other EventSync/loading messages remain native. Full host-only
input and guest failure handling are NOT implemented. No fabricated readiness,
timer, polling, ANT replay or broad guest mute. Emulation is not gameplay proof.

Live mit Nutzer / with user:
1. Spiel/Server beenden, frische Save-Sicherung (kein Restore), beide Mod-EXEs
   bytegenau sichern. Nur diesen Kandidaten installieren, keine Experimente stapeln.
   Persönliche Grafik-/Audio-Einstellungen vor Installation sichern und erhalten;
   der Installer-Check plant neben den EXEs auch INI-Änderungen.
2. pwsh -File start_local_checkpoint_test.ps1 -PackageDirectory
   outputs\TheRun-Coop-v0.7.7-RACESTART-QTE-HOST-ACTOR-CANDIDATE-R2
   Höchstens 2 lokale Clients. Nur HOST lädt direkt 10.4. Kamera/Jack in beiden
   prüfen, dann zunächst nur HOST bedienen. Bei fehlender Szene oder Absturz stoppen.
3. Dach/Feuertreppe und kompletten Szenenabschluss prüfen; danach genau ein Retry.
   Host-only-Fortschritt nicht als garantiert voraussetzen. Bestehenden
   snapshot_qte_roles.py mit --host-candidate für Zähler nutzen, keine neuen Hooks.
4. Rückbau nur über die gesicherten EXEs mit beendetem Spiel. Saves nie zurückspielen.
