# Mod catalogue / Modübersicht

This repository contains the project's own patches/tools and integrations. A preview
or source file is not an announcement that its development candidate is released.

| Mod / tool | Purpose | Where to find it |
|---|---|---|
| Story Co-op native patches | NPCs, team results, Battle phases, story roles and starts | Published package `patches/`, source under `src/` |
| Bilingual launcher | Host/Join/Solo, difficulty, graphics, updates | `Connect-Coop.ps1`, language guides |
| Garage | Own-player car selection and host relay | `Garage-Fenster.ps1`, `Garage-Core.ps1`, GARAGE-DE/EN.md |
| Music Louder and cinema mix | Reversible changes to mixer values; no songs included | `addons/music25/`, launcher music option |
| Speedometer background | Original/Dim/Clear texture-alpha patch | `mods/hud-background/` in this repository; next-package integration pending |
| QTE local-actor / host milestones | Experimental story actor selection and two10.4 milestones | Development documentation; not a complete QTE sync guarantee |
| Installer and runtime hardening | Portable PowerShell7, verified staging, safe cleanup and preflight | Development candidate, being integrated |
| Garage favorites / presets | Personal favorites and named car/pack/paint combinations | Development preview; not yet public release |
| Session / diagnostics / repair | Version check, launcher peers and opt-in bounded local logs | Development preview; no automatic log upload |

## Music versions

The historical **Music Louder +25dB** edition and the later revised cinema mix are
different presets. Current development target: Global_Music unchanged, race music
+6dB on the Film Experience film side, premixed scenes +8dB, affected car groups
rebalanced. Original/earlier known patch states are recognized for safe restoration.
Use the description shipped with your downloaded version.

## Deutsch

Die Sammlung umfasst unsere Koop-Patches, Launcher/Garage, Musikpatches und den
Tacho-Hintergrundpatch. Definitive Edition und der zugrunde liegende LAN-Mod sind
Fremdprojekte mit eigenen Credits. Nicht jeder Entwicklungsstand ist veröffentlicht
oder durch einen kompletten Kampagnentest bestätigt.

Saves, Videos, Dumps, persönliche Einstellungen und vollständige Spielbinärdateien
gehören nicht in das öffentliche Repository. Die Screenshots sind isolierte
Oberflächenvorschauen ohne Nutzerdaten.
