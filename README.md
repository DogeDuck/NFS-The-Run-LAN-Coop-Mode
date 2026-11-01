# NFS: The Run LAN Coop Mode

**v0.6 TEST – team-result adapter and optional starting-car selection. Experimental two-player story co-op.**

[Download v0.6 installer ZIP](https://github.com/DogeDuck/NFS-The-Run-LAN-Coop-Mode/raw/refs/heads/main/downloads/TheRun-Coop-v0.6-TEST.zip) · [Deutsche Anleitung](LIESMICH.md) · [Radmin setup](RADMIN-ANLEITUNG.md)

Both players need their own compatible game installation and the supported LANScript v1 base package dated May29,2024. Extract the complete ZIP, close game/server and run Install-Coop.cmd. Select the game **folder**, then use Koop-Starten.cmd. One player hosts; the other enters the host's Radmin IPv4. Only the host starts the event. Updates from supported v0.3/v0.4/v0.5 installations are included.

## Included

- **Team-result adapter:** normal Story mode0 finish-time/rank checks use the first real finished human for both players. Native win thresholds remain intact. The two humans are identified afresh on each check; bots are excluded. This is not a universal replacement for scripted failures, arrests, QTE outcomes or every progression condition. Shared overtaken HUD and shared overall Run Position / campaign rank are not included. Battle/eliminator-style opponent-defeat events can still count the teammate as an opponent; this intermediate evaluation is not fixed by the mode0 finish adapter.
- **Optional starting car:** each player can choose R35, M3 GTS, 370Z, V12 Vantage, R8, 911 Carrera S or Shelby Super Snake in the launcher. Open **VIEW CARS** once in the main menu before the host starts the race. Default: keep the Story car. The chosen car remains forced for the session; restart to change it. Use the default for scripted story car-selection sequences. See STARTAUTO.md in the ZIP.
- Native AI-racer capacity/quota fix and authored starting positions for an explicit list of38Stage2+ races, carried over from v0.5. Second human starts8m behind; Stage1 is excluded from the new grid mechanism. The older narrow1.51 recovery remains.
- Definitive Edition:240FPS target, engine-audio/particle fixes, QTE simulation clamp, faster-loading VSync bypass,4096shadows and600shadow distance. No difficulty/traffic/camera mode overrides.
- Idempotent music+25dB patch; effects-2dB and original speech.

## Validation and known issues

R35 HOST and M3 GTS GUEST were confirmed driveable in3.5 using the new pre-start selection. Native AI counts and correct3.5start spawns were confirmed in earlier tests. The other37spawn entries and the full campaign remain unverified. In3.5, the user confirmed both players win and continue together with the dynamic team adapter. Other events and scripted failure paths remain unverified. See v0.6-validation.json.

**Tank-station changes remain broken: avoid them.** No experimental garage-loading hooks are shipped. Pause-menu AI takeover, general cinematic fixes, the1.51bridge crash, shared overtaken HUD and complete story-progression support remain open. Cutscene characters, camera, audio and control transitions can still fail. Scripted police/world streaming are separate from the restored racer population.

Installation backs up changed files; launchers back up current saves without restoring older progress. Both players must use the same version. No game/server executables or game assets are distributed; the ZIP contains deltas, scripts and the licensed Definitive Edition addon.

## Source and rollback

[Team-result / starter source](src/story-coop-v0.6) · [Native AI/spawn source](src/story-coop-v0.5)

Definitive Edition: [BadassBaboon/NFS-TheRun-DE](https://github.com/BadassBaboon/NFS-TheRun-DE), commit048ab8fadbe3938f5651e9dabf09b3db64a6dc7d; MIT license included. Vehicle references: [mRally2 research](https://github.com/mRally2/The-Run-Tools-Research).

Restore-Installation.cmd restores backed-up installation files. Restore the audio mix separately as described in ADDONS.md; neither action restores saves.

ZIP SHA256: `f0dc47dcec46fceb680acb28fd01678d84c94505f78b8a515a5998e5fa59489a`
