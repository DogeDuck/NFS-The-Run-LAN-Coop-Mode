# NFS: The Run LAN Coop Mode

Experimental story co-op patches and Windows launchers for **Need for Speed: The Run**.

This prototype builds on [NFSTR_LANOnlineHelper](https://github.com/hypernucle/NFSTR_LANOnlineHelper). It is not a replacement for the game or the LAN base package: **no game executables, server binaries, loader DLLs, ASI binaries or game assets are included**.

**Status:** tested with two local clients on one Windows PC. A real two-PC Internet session and a complete campaign playthrough have not yet been validated.

[Deutsche Installationsanleitung](LIESMICH.md)

## Current behavior

- Both players can drive separate cars and see each other in the story mission tested.
- Select uses the game's normal road recovery instead of initiating a story rewind.
- Timeout or a wreck restarts the entire event for both players. This deliberately replaces checkpoint rewind, which previously left clients stuck at `RESETS LEFT`.
- Both clients display the existing shared story countdown. The guest HUD patch does not introduce a second countdown or expiration trigger.

These behaviors were confirmed during local two-client testing. They do not establish that every mission, event type or campaign transition works.

## Requirements

- Windows with Windows PowerShell 5.1 or later. The portable installer does not require Python.
- A local game installation on each PC that starts successfully before applying the mod.
- The matching locally supplied **NFSTR LANScript v1 base package dated May 29, 2024**. Existing compatible LAN files can also be used. The installer validates exact SHA-256 hashes and refuses unsupported builds.
- A shared LAN or virtual LAN between the two PCs. The tested dedicated server listens on **UDP 25200**. Internet gameplay through a virtual LAN remains unverified.

## Install and play

1. Download this repository using **Code → Download ZIP** and extract it completely.
2. Close the game and dedicated server. Run `Install-Coop.cmd` on each PC and select the actual installation folder. If required, supply the directory containing your own extracted LAN base package.
3. Establish your shared LAN or virtual LAN. See the [official Radmin VPN guide](https://www.radmin-vpn.com/help/) if using Radmin VPN.
4. The host runs `Start-Host.cmd`. The guest then runs `Start-Guest.cmd` and enters the host's LAN/VPN IPv4 address.
5. Once both game windows are open, the host presses Enter in the launcher to start the dedicated server. Once both players are connected, only the host selects **THE RUN → Continue**.

The host and guest use separate nicknames by default. Keep the launcher open until the game closes. No private host addresses or network passwords are embedded in this repository.

The launchers back up the existing `Documents\NFSTR` profile before starting. Co-op play then saves normally. Multi-mission campaign progress has not yet been validated.

## Stop and restore

`Stop-Coop.cmd` stops only the processes recorded for the current launcher session, checking their executable paths and start times.

`Restore-Installation.cmd` restores files from before that package installation. If a LAN mod was already present beforehand, that earlier LAN installation is the restored baseline. Save files are not changed by this rollback.

Backups are stored under `%LOCALAPPDATA%\TheRunStoryCoop`. Modified or unknown files are not overwritten blindly.

`Enable-HostFirewall.ps1` is an optional, separately invoked helper for allowing the dedicated server's UDP port from one specified peer address. It is not run automatically.

## Known limitations

- A story cutscene was observed below the map.
- Full race completion, chapter transitions and long-term campaign persistence are untested.
- Internet gameplay and separate physical PCs are untested.
- Automatic recovery restarts the full event, rather than restoring a story checkpoint.
- One controller can affect both windows during local two-instance testing; each player should use their own input device on their own PC.

## Implementation

The portable installer applies the version-locked binary deltas in `patches/`. The reference Python generators in `src/` document the native adapters and their guards. They require locally supplied original files and backups and are not needed to install the portable package.

The patches address the dedicated server's inactive streaming settle counter, manual road recovery, shared event retry, and the guest's publication of the player-0 story timer to the HUD. Code adapters use separate executable/read-only code and writable diagnostic sections.

`validation.json` records the prototype's validation scope. The installer and rollback were checked under Windows PowerShell 5.1 against an isolated copy of the LAN files, including hash verification and rejection of an altered unsupported executable.

## Credits

LAN foundation: **Hypercycle / And799 / mRally2**, [NFSTR_LANOnlineHelper](https://github.com/hypernucle/NFSTR_LANOnlineHelper), MIT license. The derived configuration's notice is included in [LICENSE-LANOnlineHelper.txt](LICENSE-LANOnlineHelper.txt).
