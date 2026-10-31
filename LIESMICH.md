# The Run Coop v0.3 TEST – experimenteller Zweispieler-Test

Beide brauchen eine eigene passende Spielinstallation und das unterstützte
LAN-Grundpaket v1 vom 29.05.2024. Keine Spieldateien enthalten.

1. Spiel und Server schließen. Install-Coop.cmd auf beiden PCs starten.
2. RADMIN-ANLEITUNG.md befolgen. Koop-Starten.cmd bietet Host/Gast und ein IP-Feld.
3. Im Host-Starter erst Enter drücken, wenn das Gast-Spielfenster offen ist.
4. Nur der Host startet die Story. Das Starterfenster bleibt währenddessen offen.
5. Stop-Coop.cmd beendet die eigene Sitzung; Restore-Installation.cmd stellt die
   vor der Installation gesicherten Dateien wieder her. Spielstände werden vor
   jedem Start gesichert und nicht automatisch zurückgeschrieben.

Enthalten: gemeinsame Checkpoint-Zeit, gezielte Spawnkorrektur für Mission 1.51,
experimenteller Resetmodus und Sitzungs-Fahrzeugfreigabe. Ein Unfall des Hosts
ließ den Gast in einem aufgezeichneten Test weiterfahren. Diese Paketkombination
ist noch nicht als Ganzes im Spiel getestet.

Select soll in 1.51 einen gemeinsamen Event-Neustart anfordern. Zeitablauf,
beide Autos zerstört und blockierte Eingaben sind noch nicht zuverlässig gelöst.
Automatischer Folgeevent-Wechsel ist offen. Nur als Diagnose-Workaround: Host
drückt einmal Next Challenge im Debugmenü, falls derselbe Event erneut beginnt.
Das überspringt Storyteile und garantiert keinen korrekten Folgespawn.

Bekannte Fehler: fehlende Gegner/Verfolgung in der zweiten getesteten Mission,
unvollständige Gast-Cutscenes, falsches Gastauto, fehlender Host-Sound/Nitroeffekt,
keine gemeinsame Pause. Kein Nachweis für alle Missionen oder zwei Internet-PCs.
Musik-25dB-Mod und allgemeiner Car-Swap-Fix sind nicht enthalten.
