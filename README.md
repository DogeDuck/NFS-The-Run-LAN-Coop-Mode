# NFS: The Run LAN Coop Mode

**v0.5 TEST – native AI racers and story start spawns. Experimental two-player co-op.**

[Download v0.5 installer ZIP](https://github.com/DogeDuck/NFS-The-Run-LAN-Coop-Mode/raw/refs/heads/main/downloads/TheRun-Coop-v0.5-TEST.zip) · [Deutsche Anleitung](LIESMICH.md) · [Radmin setup](RADMIN-ANLEITUNG.md)

Both players need their own compatible game installation and the supported LANScript v1 base package dated May29,2024. Extract the whole ZIP, close game/server, run Install-Coop.cmd and select the game **folder**. Updates from v0.3/v0.4 are supported. Run Koop-Starten.cmd: one Host, one Guest; the Guest enters the Host's Radmin IPv4. Only the Host starts the race.

## What changed

- Restore native story AI racer filling, with guards for free grid capacity. The second human should not displace an original NPC when capacity permits. Scripted police and world streaming remain separate.
- Use the authored single-player start ordinal and native server spawn transform for an explicit list of **38 races from Stage2 onward**. The second processed human starts8m behind the same anchor; engine processing order determines which human is first. Original grid entities/ownership remain intact.
- The new start-spawn logic excludes Stage1; the existing narrowly scoped1.51 client recovery remains unchanged.
- Definitive Edition with the restricted co-op configuration and the +25dB music patch remain included. See ADDONS.md inside the ZIP.

## Actual validation and limits

**Confirmed in game: both cars start correctly and are driveable in3.5 after a full Retry.** Native counters recorded two human grid selections and one spawn-matrix correction per car. Native AI racers and preservation of the original opponent count were separately confirmed in earlier local tests. The other37 spawn entries have not been tested in game. The combined disk package has not been tested as a complete campaign or on two PCs.

Tank-station vehicle changes are **not fixed**: missing preview/endless loading/softlock remain; avoid them for now. Pause-menu AI takeover, the newer team-win prototype, shared overtaken HUD and general cinematic fixes are not included. The1.51 bridge crash remains unresolved. Progression, audio and camera issues may still occur. No experimental garage-routing hooks or automatic diagnostic recordings are shipped.

The ZIP includes SPAWN-EVENTS.json, GAMEPLAY-STATUS.json, the German Radmin guide and reversible installation scripts. No game or server executables are distributed. Installers back up changed installation files; launchers back up saves without automatically restoring old progress. Both players must use the same version.

ZIP SHA256: `9107f2e2749cc7b29180a2e84e2de5316808b2f85239a707844f92d39ac5108a`

## Sources and rollback

[Native spawn/AI source](src/story-coop-v0.5) · [Changelog](CHANGELOG.md)

Definitive Edition: [BadassBaboon/NFS-TheRun-DE](https://github.com/BadassBaboon/NFS-TheRun-DE), commit048ab8fadbe3938f5651e9dabf09b3db64a6dc7d; MIT license included. The existing local music patch is bundled idempotently. Original game/LAN base files are still required.

Restore-Installation.cmd restores files backed up by this installer. Restore the music mix separately as described in ADDONS.md inside the ZIP. Installation restores do not restore saves.
