# Sitzung, Garage und Diagnose

Starte den Host zuerst über **Host**, danach die anderen PCs über **Beitreten**.
Alle benötigen dieselbe Paketversion sowie dieselben Client-/Server-Patches.
Der Launcher prüft dies vor dem Gast-Spielstart über TCP25212. Der Spielverkehr
verwendet weiterhin UDP25200; die Garage verwendet TCP25211. Bei Bedarf den
Firewall-Helfer für die einzelne VPN-Adresse jedes Mitspielers verwenden.

Die **Sitzungsübersicht** zeigt die Kontakte der Launcher, ihre Namen/Versionen
und den Diagnosezustand. Sie ist keine Anzeige der tatsächlichen Rennplatzierung.
Das native Spielerlimit für drei/vier PCs ist noch nicht vollständig im Spiel
bestätigt. Bitte keine vier lokalen Spielinstanzen zum Testen starten.

## Garage

Das Garage-Fenster öffnet sich mit dem jeweiligen Koop-Client. Jeder wählt sein
eigenes Auto; das Host-Fenster vermittelt die Gast-Auswahl. Beide Fenster offen
lassen, damit die Wahl beim nächsten Rennen und nach Retry gehalten wird.

**Favorit** merkt ein Auto. **Nur Favoriten** filtert die Liste. Ein benanntes
**Fahrzeugset** merkt Auto, Style-Pack und Lackvariante. **Set laden** wählt diese
Kombination aus; erst **Übernehmen** sendet sie an das Spiel. Favoriten/Sets liegen
persönlich in `%LOCALAPPDATA%\TheRunStoryCoop\garage-profiles.json` und bleiben bei
Updates erhalten. Ein Set ersetzt keinen Spielstand und schaltet keine Story frei.

## Freiwillige Diagnose

Der Haken **Diagnose speichern (dieser PC)** ist standardmäßig aus. Jeder Spieler
entscheidet selbst. Bei eingeschalteter Diagnose schreibt sein Starter begrenzte
JSONL-Dateien nach:

`SPIELORDNER\TheRun-Coop-Logs\SITZUNG-ROLLE-SPIELERNAME\`

Erfasst werden ungefähr alle fünf Sekunden Version, Rolle, CPU-Zeit, RAM und der
Launcher-Verbindungsstatus, beim Beenden möglichst auch der Prozess-Endcode.
Die Dateien rotieren: höchstens drei Dateien zu ungefähr2MB. Es werden keine
Speicher-Hooks, Frida-Sonden, Eingaben, Videos oder automatischen Uploads gestartet.
Die tatsächlich entstehende Laufzeitlast ist noch nicht im Spiel gemessen.

Ohne den Haken entstehen keine Diagnose-Zeitreihen. Kleine Verwaltungsdateien
für die Sitzung, Versionsprüfung und vorhandene Spielstandsicherungen bleiben
Teil des Starters. Die Garage verwendet ihre vorhandene Laufzeit-Anbindung für
die Autoauswahl; das ist unabhängig von der Diagnoseoption.

Für die lokale Support-Auswertung ausschließlich:

```text
python coop_summary.py --launcher-logs "PFAD ZUM SPIELER-LOGORDNER"
```

Keine Datei oder ein fehlender Endcode beweist keinen erfolgreichen Lauf oder
Absturz. Die Diagnose allein bewertet weder QTEs noch Kamera, FPS oder Rennen.

## Reparatur und Updates

**Moddateien prüfen / reparieren** rekonstruiert bekannte native Moddateien aus
den geprüften Paket-Deltas und eigenen Installationssicherungen. Fehlt eine
passende Quelle, wird der Vorgang abgebrochen. Persönliche INIs und Spielstände
sind keine Reparaturziele. Diese Funktion ist keine Vollreparatur sämtlicher
Spieldaten oder beschädigter Audio-/HUD-Archive.

Updates werden vor dem Wechsel vollständig geprüft. Vorhandene persönliche
INIs, Grafik-/Musik-/HUD-Auswahl, Garage-Profile und unbekannte Einstellungsfelder
bleiben erhalten. Alte Paketordner werden erst nach bestätigter Installation
bereinigt; eigene oder veränderte Dateien verhindern ihre automatische Löschung.
Fehlendes PowerShell7 wird aus der offiziellen Microsoft-Veröffentlichung mit
Prüfsumme und Signaturprüfung pro Benutzer bereitgestellt.

Dieser Entwicklungsstand wurde offline geprüft. Der Gesamtkandidat und die
experimentellen Szenen-/Stations-/Team-Fixes benötigen einen gemeinsamen Spieltest.
Eine vollständige HOST-QTE-Synchronisierung ist noch nicht enthalten.
