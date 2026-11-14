# The Run: Film-Experience-Reglermix / Slider audio mix

Wird vom Koop-Installer automatisch angewendet. Das Spiel kann danach normal gestartet werden.

| Kanal | Änderung gegenüber dem Original |
|---|---:|
| Musik gesamt | unverändert, kein globaler Boost |
| Rennmusik (Brian Tyler/Soundtrack beim Fahren), Regler „Film Experience“ rechts | +6 dB |
| Spielerauto (Motor, Reifen, NOS), Gegner, Lkw, Regler rechts | −4 dB |
| Story-Szenen, QTE-Momente, Credits-Score („MomentStreams“) | +8 dB |
| Effekte, Umgebung, Menütöne | −2 dB |
| Sprache / Speech | 0 dB |

## Regler „Film Experience“

Dies ist die einzige angebotene Audioversion. Der alte feste +25-dB-Patch wird
nicht mehr installiert und ist keine auswählbare Option.

- **Rechts (Standard):** mehr Musik, leisere Autos (Werte oben).
- **Links:** wie im Originalspiel auf der Renn-Seite (Rennmusik −5 dB, Autos +2…+5 dB).
  Dazwischen wird stufenlos gemischt.

## Szenen

Story-Zwischensequenzen und QTE-Momente haben eine fertig gemischte 5.1-Tonspur. Darin stecken Musik, Effekte
und teils der Szenendialog zusammen. Diese Szenen werden deshalb als Ganzes um 8 dB lauter; nur die Musik darin
getrennt anzuheben ist ohne Neuabmischung der Audiodateien nicht möglich.

## Anwenden und Wiederherstellen

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ".\NFS-Audio-Patch.ps1" -GamePath "D:\Spiele\The Run" -Mode Apply
pwsh -NoProfile -ExecutionPolicy Bypass -File ".\NFS-Audio-Patch.ps1" -GamePath "D:\Spiele\The Run" -Mode Restore
```

Das Skript erkennt Originaldateien sowie die früheren Musik-Patches mit +3, +10 und +25 dB und setzt absolute
Zielwerte: Wiederholtes Anwenden verstärkt nichts weiter. `-Mode Restore` stellt den originalen Audiomix her.
`-CheckOnly` prüft nur und schreibt nichts.

English: Only the Film Experience slider mix is offered. Global music gain stays
unchanged. Older boost states are recognized only for migration and exact
restoration; they cannot be selected as installation targets.

## Prüfung und Grenzen

Vor jedem Schreibvorgang prüft das Skript sämtliche betroffenen Stellen, danach alle 335 betroffenen
Audio-Asset-Kopien (Basis- und Update-Bundles) per SHA-1. Bei einem Fehler setzt es begonnene Änderungen zurück.
Unbekannte oder abweichende Dateistände werden vor dem Schreiben abgelehnt.

Sehr hohe Verstärkung kann Spitzen begrenzen oder verzerren. Ein Hörvergleich im Spiel steht noch aus.

Spieldaten untersucht mit den quelloffenen Frostbite-Scripts von NicknineTheEagle:
https://github.com/NicknineTheEagle/Frostbite-Scripts
