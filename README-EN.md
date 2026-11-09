# v0.7.4-TEST

[Changes / Änderungen](CHANGELOG.md)
[Updates and difficulty / Updates und Schwierigkeit](UPDATES-DIFFICULTY.md)

# The Run Story Co-op – English

[Deutsch](README-DE.md) · [Set up Radmin](RADMIN-EN.md) · [Garage](GARAGE-EN.md)

Experimental story co-op test package. Each player needs their own supported game installation and the same mod package. The download contains patches, launchers and mods, not game or server executables. See `GAMEPLAY-STATUS.json` and the included release notes for the exact version, enabled patches and verification limits.

## Install and play

1. Extract the entire ZIP. Close the game and co-op server.
2. Run `Install.cmd` (an alias for the existing `Install-Coop.cmd` installer). Enter the **game folder** containing `Need For Speed The Run.exe`. If requested, provide your own extracted LAN base package v1 dated 29 May 2024. Do not rename executables to bypass version checks.
3. For separate PCs, [set up Radmin](RADMIN-EN.md).
4. Open `Launch-Coop.cmd`, choose English, and enter your game folder and player name. `Launch-Coop.vbs` opens the same interface without a persistent command window. The German `Koop-Starten.cmd` alias still works.
5. One player selects **Host**. Guests select **Join** and enter the host's Radmin IPv4 address without a port.
6. The host presses Enter in the launcher console once all guest game windows are open. This starts the server. Only the host selects the story/Continue. Keep launcher consoles and garage windows open during the session.

**Solo** starts single player with the installed mods. The launcher disables the LAN option for that session and restores it afterward if nothing else changed it. The game still saves normally.

PowerShell 7 is required. An existing suitable installation is used; this package does not install it automatically yet. See [Microsoft's PowerShell installation instructions](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows).

## Language and preferences

The launcher and garage support German/English. Language is saved only on your PC. The default follows the Windows UI language: German for German Windows, English otherwise. Your name, host IP, game folder and local window preferences are remembered. Each player selects their own car in the [garage](GARAGE-EN.md).

The host can select the intended server limit from 1–4. Full four-player operation has not been confirmed in a live test; local tests use at most two game clients. Choose difficulty in the game for now. Launcher difficulty control and automatic host-to-guest synchronization remain unfinished. There is no switch to disable AI driving while paused.

## Limits and backups

- Avoid gas station car selection: preview, loading and returning can get stuck. Use the garage between missions.
- Cutscenes, host/guest cameras, QTEs and scripted race endings can still fail. One successful test does not establish that the full campaign works.
- The installer backs up modified installation files. Co-op starts back up your current save; they never restore an older save automatically.
- Close your own game window or use `Stop-Coop.cmd`. `Restore-Installation.cmd` restores backed-up installation files, not game saves. Audio restoration is separate; see `ADDONS.md`.

## Installer prompts that are still German

- `Vollstaendiger Spielordner (enthaelt die Spiel-EXE)`: enter the full game folder.
- `Ordner des entpackten eigenen LAN-Grundpakets v1 vom 29.05.2024`: enter your extracted LAN base package folder.
- `Bitte Spiel und Testserver zuerst schliessen`: close the game and test server first.
- `Passende LAN-Grunddatei fehlt`: the required supported base file is missing; provide your own supported LAN package.
- `Originaldateien`: location of the installation backup.

**Translation coverage:** launcher, garage and these guides are bilingual. The existing installer, restoration, firewall helper, diagnostics and some addon notes still contain German messages. Full package translation is not complete yet.
