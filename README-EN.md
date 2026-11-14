# Installation — v0.7.8-TEST

1. Close the game/server. Install your legally owned supported PC game and the required LAN base mod on each PC.
2. Download and fully extract TheRun-Coop-v0.7.8-TEST.zip. Keep the whole folder, not just the installer.
3. Run Install.cmd and select your game folder. It checks supported hashes, backs up changed installation files and preserves personal INIs. PowerShell7 is provided when needed. Saves are never restored.
4. Run Launch-Coop.cmd or Launch-Coop.vbs. Choose Host / Join / Solo; guests enter the host VPN IPv4. Use matching packages on every PC and follow [Radmin setup](RADMIN-EN.md).
5. Only the host starts Story. Keep every garage open to retain car choices. The host QTE helper starts automatically. If required, allow friend-only TCP25211/25212 and UDP25200/25214 using Enable-HostFirewall.ps1 on the relevant PCs.

[Features / showcase](README.md) · [Session, garage and diagnostics](SESSION-EN.md) · [Changes and known issues](CHANGELOG.md)

TEST build: new combined gameplay, remote QTE transport, cutscene control/lights and full4-PC compatibility remain unverified. Back up your saves before testing. The old fixed25-dB audio profile is not offered.
