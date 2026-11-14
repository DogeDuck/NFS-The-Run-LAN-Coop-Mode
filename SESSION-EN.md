# Session, garage and diagnostics

Start **Host** first, then **Join** on the other PCs. All players need the same
package version and client/server patches. The launcher checks this before
starting a guest game using TCP25212. Gameplay still uses UDP25200 and the garage
uses TCP25211. If required, run the firewall helper for each friend's VPN address.

**Session overview** shows launcher contacts, names, versions and diagnostic
status. These contacts are not native race standings. Full three/four-PC gameplay
support remains unverified. Do not run four local game instances for testing.

## Garage

The garage opens with each co-op client. Everyone chooses their own car; the
host garage relays guest choices. Keep both garage windows open so the chosen
car remains selected for subsequent events and Retry.

**Favorite** remembers a car; **Favorites only** filters the list. A named
**preset** stores the car, style pack and paint variant. **Load preset** selects
that combination; **Apply** confirms it with the game. Personal favorites and
presets are stored in `%LOCALAPPDATA%\TheRunStoryCoop\garage-profiles.json` and
survive updates. Presets do not replace saves or unlock story progress.

## Optional diagnostics

**Save diagnostics (this PC)** defaults to off. Each player decides independently.
When enabled, bounded JSONL files are stored under:

`GAME FOLDER\TheRun-Coop-Logs\SESSION-ROLE-NICKNAME\`

Version, role, CPU time, RAM and launcher connection status are sampled about
every five seconds. The game exit code is recorded when available. Logs rotate
between at most three files of about2MB each. This does not start memory hooks,
Frida probes, synthetic input, video recording or automatic uploads. Actual
runtime overhead has not yet been measured in gameplay.

With the box unchecked, diagnostic time series are not written. Small launcher
session/version metadata and existing save backups remain part of the starter.
The garage retains its existing runtime connection for car selection, independent
of the diagnostic option.

For local support summaries, use only:

```text
python coop_summary.py --launcher-logs "PLAYER LOG FOLDER"
```

Missing logs or an absent end code do not establish success or a crash. These
logs cannot judge QTE completion, camera correctness, FPS or race behavior.

## Repair and updates

**Check / repair mod files** reconstructs known native mod files from verified
package deltas and your own installation backups. Missing verified source bytes
stop the operation. Personal INIs and game saves are never repair targets. This
does not repair every game asset or damaged music/HUD archive.

Updates are fully verified before switching packages. Existing personal INIs,
graphics/music/HUD choices, garage profiles and unknown preference fields are
preserved. Old package directories are cleaned only after a verified installation;
personal or modified files prevent automatic removal. Missing PowerShell7 is
provisioned per user from Microsoft's official release, with checksum and
signature verification.

This development work was tested offline. The complete candidate and experimental
scene/station/team changes still need joint gameplay tests. Complete host-only
QTE synchronization is not included yet.
