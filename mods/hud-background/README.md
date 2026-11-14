# Speedometer background / Tacho-Hintergrund

Our reversible UI-alpha patch. Close the game first. The script checks every
patch location before writing; supported states are Original, Dim and Clear.
No game archive is distributed. Locally installed/tested as an asset patch;
the next combined public package is pending.

```powershell
pwsh -File NFS-HUD-Patch.ps1 -GamePath "YOUR GAME FOLDER" -Mode Apply -Variant Dim
pwsh -File NFS-HUD-Patch.ps1 -GamePath "YOUR GAME FOLDER" -Mode Restore
```

Deutsch: Spiel vorher schließen. Dim = 15%, Clear = Hintergrund ausgeblendet.
QTE-Tasten werden nicht ausgeblendet. Vorher eigene Dateien sichern.
