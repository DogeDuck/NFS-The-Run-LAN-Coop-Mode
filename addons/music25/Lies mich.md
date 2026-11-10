# The Run: Audio-Patch

Auf deinem PC bereits angewendet. Das Spiel kann danach normal gestartet werden.

| Kanal | Änderung gegenüber dem Original |
|---|---:|
| Musik | +25 dB insgesamt |
| Motoren, Effekte, Umgebung, Menütöne | −2 dB |
| Sprache / Speech | 0 dB |

Die vorhandenen Musiksegmente werden weiterhin vom Spiel gesteuert. Übergänge,
Tempo- und Levelsteuerung sowie Dialog-Ducking bleiben erhalten. Der Patch
ändert die Grundpegel der passenden Mixergruppen und drei feste Szenenwerte.
Gemeinsame Master- und Hallsteuerungen bleiben erhalten, damit Sprache nicht
über einen gemeinsamen übergeordneten Kanal mit abgesenkt wird.

## Speichern und später anwenden

1. Diesen Ordner oder die ZIP-Datei aufbewahren.
2. The Run und den DLSS-Host vollständig schließen.
3. ZIP gegebenenfalls entpacken und `Anwenden.cmd` öffnen.

Der Patch erkennt Originaldateien sowie die vorherigen lokalen Musik-Patches
mit +3 und +10 dB. Er setzt absolute Zielwerte: Wiederholtes Anwenden verstärkt
die Musik nicht weiter.

`Original wiederherstellen.cmd` setzt die geänderten Stellen auf den ursprünglichen
Audiomix zurück. Es stellt nicht den vorherigen +10-dB-Mix her.

## Copy-and-paste

`Copy-Paste-Patch.txt` enthält den vollständigen eigenständigen PowerShell-Aufruf.
Den gesamten Inhalt in PowerShell kopieren und ausführen. Am Ende steht der
Spielordner; dieser kann bei einer anderen Installation angepasst werden.

Alternativ reicht diese einzige Datei: `NFS-Audio-Patch.ps1`. Sie enthält alle
Patchdaten und alle Originalbytes, benötigt weder Python noch Downloads.
Liegt sie direkt neben der Spiel-EXE, verwendet sie diesen Ordner. Andernfalls
verwendet sie den ursprünglich untersuchten Installationspfad:

`X:\EA Games\Need for Speed The Run\Need for Speed The Run`

Für einen anderen Ordner:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\NFS-Audio-Patch.ps1" -GamePath "D:\Spiele\The Run" -Mode Apply
```

Zum Wiederherstellen `-Mode Restore` verwenden.

## Prüfung und Grenzen

An der hier untersuchten PC-Installation vorbereitet und angewendet. Unbekannte
oder abweichende Dateistände werden abgelehnt. Dies ist kein universeller Patch
für beliebige Spielversionen.

Vor jedem Schreibvorgang prüft das Skript sämtliche betroffenen Stellen.
Anschließend prüft es die vollständigen 94 betroffenen Audio-Assets sowie ihre
SHA-1-Prüfsummen. Bei einem Fehler setzt es bereits begonnene Änderungen zurück.
Dieses Verhalten wurde zusätzlich an separaten Beispieldateien mit Original-,
+3-dB- und +10-dB-Ausgangszuständen geprüft, einschließlich Fehlerabbruch und
Wiederherstellung. Die Sprachkanäle werden bei der Erstellung ausgeschlossen.

+25 dB ist ein großer Boost; der Spielmix kann laute Spitzen begrenzen oder
verzerren. Ein Hörvergleich im Rennen ist noch erforderlich.

Die Spieldaten wurden mit den quelloffenen Frostbite-Scripts von NicknineTheEagle
untersucht: https://github.com/NicknineTheEagle/Frostbite-Scripts
