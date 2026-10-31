# NFS: The Run LAN Coop Mode

**v0.3 TEST: experimental two-player story co-op. Not a complete campaign mod.**

[Download portable test installer](downloads/TheRun-Coop-v0.3-TEST.zip?raw=true) · [Deutsche Anleitung](LIESMICH.md) · [Radmin verbinden](RADMIN-ANLEITUNG.md)

Extract the ZIP completely. Both players need their own supported game installation
and matching NFSTR LANScript v1 base package dated May 29, 2024. No game executables,
server binaries, loader DLLs or game assets are distributed here.

Run `Install-Coop.cmd` with game and server closed, then use `Koop-Starten.cmd`.
Choose Host or Guest; the guest enters the host's Radmin IPv4 in the IP box.
The host presses Enter in the launcher once the guest game window is open.
Keep the launcher console open. Only the host starts the story.

This package combines shared checkpoint time, a narrowly scoped mission 1.51 spawn
recovery, experimental reset handling and session-only garage unlocks. The spawn
prototype and shared timer were tested locally. One recorded host wreck left the
guest driving for over two minutes. **The combined disk package and separate-PC
Internet gameplay have not yet been tested in game.**

Known problems include timeout/retry softlocks, incomplete story progression,
missing racers/pursuit in the second tested mission, guest cinematic assets/camera,
guest car selection and missing host audio/nitro effects. There is no shared pause.
Manual `Next Challenge` is a diagnostic workaround that may skip story content.
See the German instructions for the exact limits and rollback steps.

The installer checks exact SHA-256 baselines and backs up installation files.
Launchers back up the current save profile before starting. Restore-Installation
restores installation files, not your saves. Music mods are not included.

LAN foundation: [NFSTR_LANOnlineHelper](https://github.com/hypernucle/NFSTR_LANOnlineHelper),
Hypercycle / And799 / mRally2, MIT; see LICENSE-LANOnlineHelper.txt.
