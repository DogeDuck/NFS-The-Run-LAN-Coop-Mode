# v0.3 TEST – launcher hotfix

- Fix Windows PowerShell Point constructor argument parsing that closed the GUI immediately.
- Add a hidden form-construction validation mode; verified all 11 controls without launching the game.
- Keep the console open on a launcher startup error.
- Game patches unchanged; existing users only need the updated starter files.

# v0.3 TEST

- Add portable Host/Guest GUI with Radmin IPv4 entry and German connection guide.
- Package shared checkpoint registration/time and scoped mission 1.51 spawn recovery.
- Include experimental reset acknowledgement/manual retry policy and garage unlock worker.
- Support exact-hash upgrades from v0.1 and the local research baseline.
- Known missing AI/pursuit, transitions and timeout/retry issues remain open.
- Offline checks pass; combined package still needs in-game and two-PC testing.

# Changelog

## 0.1 – 2026-10-29

- Add experimental story co-op patches for the supported LAN client and server.
- Route manual Select recovery to the existing road reset path.
- Replace automatic story checkpoint restore with a shared full-event retry.
- Publish the existing shared story countdown to the guest HUD.
- Add portable PowerShell installation, host/join launchers, profile backup and guarded rollback.
- Document local two-client validation and the remaining Internet/campaign limitations.
