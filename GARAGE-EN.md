# Garage – choose your own car

[Deutsch](GARAGE-DE.md) · [Installation and start](README-EN.md)

1. The garage opens automatically when you start co-op. To open it manually, use `Launch-Garage.cmd`; the German `Garage-Fenster.cmd` alias also works.
2. Choose English/Deutsch at the top right. Language stays personal and is also used the next time you open the launcher.
3. Load a race. The header shows your own player number and Host/Guest role. Keep both garage windows open: the host receives guest car selections over TCP 25211.
4. Search for a car and select it on the left, then choose a pack and variant/paint. Click **Apply for the next race**. The car appears at the next vehicle spawn/stage start or Retry, not immediately during a race. The host garage keeps that selection while its window stays open.
5. **Story car** lets the story choose the host's own car again. Returning a guest to story-controlled car selection is not implemented yet; guests can select another car instead.

Prefer changing cars between missions. Gas station car selection is still faulty; avoid it. The garage does not edit game saves, INI files or executables. It sets the verified car selection for the individual player on the running server.

When available, model photos are downloaded from Wikimedia Commons with author/license credit. A photo may not show the chosen game variant. You can drag in your own PNG/JPG/BMP or use **Capture game**, which captures only the game window. Images stay on your PC in `%LOCALAPPDATA%\TheRunStoryCoop\previews`.

A star marks an experimental fun vehicle. Police cars, buses, taxis, trucks and other vehicles are not officially driveable. Physics, cameras, spawning and story events may fail. Vehicle selection credit: [Car Changer by Enksx1 / 379Felipe](https://nfsmods.xyz/mod/282); only vehicle identifiers were reused. Tier reference: [NFS Wiki](https://nfs.fandom.com/wiki/Need_for_Speed:_The_Run/Cars).

Separate cars, style packs and retaining selections after a stage change/Retry have been checked locally. A local guest also uses the relay. This does not establish connectivity through another PC's firewall or complete four-player operation.
