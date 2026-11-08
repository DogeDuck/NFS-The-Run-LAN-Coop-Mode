# Optionale Diagnose – Entwicklungskandidat

Diese Werkzeuge lesen nur Prozesszustände. Sie ändern weder Fahrzeuge noch
Spielstände und laden nichts hoch. Python 3.10 oder neuer muss lokal vorhanden
sein; es wird nicht mitgeliefert. Ohne Python funktioniert die normale Mod weiter.

1. Koop wie gewohnt starten und verbinden. Radmin genügt; kein zweites lokales
   Spielfenster nötig.
2. Auf dem Host `Diagnose-Starten.cmd` öffnen. Auf dem Gast kann Yasin denselben
   Schritt für seinen eigenen lokalen Client machen. Fenster offen lassen.
3. Direkt nach einem Fehler optional `Diagnose-Markieren.cmd` öffnen und kurz
   beschreiben, was passiert ist. Keine IP/Passwörter eintragen.
4. Die Aufnahme endet nach höchstens 30 Minuten oder wenn der lokale Client endet.
   Für gezieltes früheres Beenden im Diagnosefenster Strg+C drücken.
5. Danach `Diagnose-Exportieren.cmd` erstellt ein lokales ZIP. Beide Pakete können
   zum Vergleich bereitgestellt werden. Es erfolgt kein automatischer Upload.

Aufbewahrt werden etwa die letzten zwei Minuten detaillierter Messwerte und bis
zu 500 Zustandswechsel. Gewöhnliche Positionsänderungen füllen die Zustandsliste
nicht. Ein Fehler, der länger zurückliegt, kann aus dem begrenzten Puffer fallen.

Speicherort: `%LOCALAPPDATA%\TheRunStoryCoop\Diagnostics`.
Der Export enthält nur ausgewählte Logs und Berichte, keine Saves oder Dumps.
Ein Crashdump kann separat erforderlich sein.

Wird Python nicht gefunden, kann der Entwickler `Start-Diagnostics.ps1` mit
`-PythonPath "C:\Pfad\zu\python.exe"` starten. Die Windows-Store-Verknüpfung wird
nicht automatisch aufgerufen.

Der Hostbericht enthält den lokalen Client und serverseitig registrierte
Teilnehmer. Gastkamera/Streaming lassen sich daraus nicht vollständig rekonstruieren.
Besondere Polizeifahrzeuge und Verkehr können außerhalb der Racerliste liegen.
Es gibt keine Bildschirm-/Videoaufzeichnung und keinen vollständigen Paketmitschnitt.

Entwicklerwerkzeuge für kurze native Aufruf-Traces bleiben separat. Sie sind
begrenzt, verwenden temporäre Hooks und müssen unmittelbar vor dem Fehler gestartet
werden. Die alte `record_finish_signals.py`-Clone-Annahme ist verworfen.

## Kompakter Bericht nach dem Test

Das Entwicklerwerkzeug `diagnostics_tool/coop_capture_summary.py` wertet einen
bereits beendeten lokalen Aufnahmeordner aus, ohne das Spiel zu öffnen:

```powershell
python diagnostics_tool/coop_capture_summary.py "C:\Pfad\zum\Aufnahmeordner"
```

Es fasst registrierte Fahrer, native Füllparameter und beobachtete Fahrzeugflags
zusammen. Überlappende Puffer zählen einmal. Unvollständige Lesevorgänge werden
gesondert gezählt. Ein Gastbericht erfindet keine serverseitigen Gegnerzahlen.
Die Stichprobenzahlen sind keine gemessenen Zeitdauern und beweisen weder einen
Sieg noch einen Neustart oder eine Absturzursache. Optional schreibt
`--output "C:\Pfad\bericht.json"` eine neue Datei; vorhandene Dateien bleiben erhalten.

## Gezielte Absturzaufnahme an der Brücke (DEV)

`Diagnose-Absturz.cmd` beobachtet den verbundenen lokalen Client für drei Minuten
(höchstens fünf über den Entwicklerparameter). Sie startet kein Spiel und
verändert weder Spielcode noch Spielstände. Python 3.10+ in **64 Bit** ist nötig.
Am Host wird der lokale Host, auf Yasins PC dessen eigener Gast beobachtet.

Diese Variante benutzt Windows-Debugereignisse. Beim Anschluss und beim Erfassen
halten die Spielthreads kurz an; das kann das zeitliche Verhalten beeinflussen.
Die Ausnahme wird an die ursprünglichen Spielhandler weitergegeben. Ein zuerst
beobachteter Speicherfehler ist deshalb noch kein Beweis eines fatalen Absturzes.
Die Windows-Anbindung ist an einem eigenen x86-Testprogramm geprüft, noch nicht
an einem erneuten NFS-Fahrtest. Keine automatische Aktivierung im Koop-Starter.

Nach dem Ende erzeugt `Diagnose-Absturz-Exportieren.cmd` ein lokales ZIP mit
Manifest und bis zu vier kleinen relevanten Speicheraufnahmen. Keine vollständigen
Prozessdumps, Saves, Videos oder automatischen Uploads. Ablage:
`%LOCALAPPDATA%\TheRunStoryCoop\CrashDiagnostics`.

Die Entwickler können ein `exception-1.json` später mit
`python diagnostics_tool/record_bridge_exception.py --replay "C:\Pfad\exception-1.json"`
ohne laufendes Spiel erneut auswerten. Der native Fehler wird durch dieses
Diagnosewerkzeug nicht repariert oder als Erfolg umgedeutet.
