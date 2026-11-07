# NFS: The Run LAN Coop Mode — v0.7 TEST

Experimental two-player story co-op using the original LAN multiplayer base.

**[Download v0.7 TEST](https://github.com/DogeDuck/NFS-The-Run-LAN-Coop-Mode/releases/tag/v0.7-TEST)** · [German setup guide](RADMIN-ANLEITUNG.md) · [Changes and limitations](LIESMICH.md)

Both players need their own supported game installation, the LAN base package v1
from May 29, 2024, PowerShell 7, and the same mod version. Game/server executables
and save files are not included. The ZIP includes an installer and file backups.

## Included

- Native AI driving while the pause menu is open, with release on resume.
- Native multiplayer player list replacing the Story clock/Autolog stage leader.
- A reserved second-human start slot on supported events, keeping NPC slots free.
- A separate Garage window for each client, launched with the game without a
  persistent console. Select a car/style/variant for the next spawn or Retry.
- Guest car requests sent through the host Garage on TCP25211; fixes the previous
  ForeColor/null confirmation error. Keep both Garage windows open.
- Existing AI population, listed Story start-position corrections, shared
  checkpoint time bonuses, and normal race team-result handling.
- Definitive Edition co-op profile and the +25dB music patch, with credits.

Host pause-AI, the visible multiplayer HUD, and the first NPC in event2.6 have
been confirmed locally. This is not a full campaign or two-PC validation.

## Known issues

Eliminator/Battle results are still per-player: a guest may lose when only the
host beats the NPC. Shared Battle opponent/phase/countdown/counters are unfinished.
Avoid gas stations; use Garage instead. Guest cinematic/QTE/camera problems,
the mission1.51 bridge crash, and some streaming/spawn/audio issues remain.
Exact HUD gap values and the new Garage relay over Radmin need further testing.

Close the game/server before installing. Run Install-Coop.cmd, then
Koop-Starten.cmd; the guest enters the host's Radmin IPv4. Only the host selects
the mission. See the included guides for ports and backups. No automatic save restore.
