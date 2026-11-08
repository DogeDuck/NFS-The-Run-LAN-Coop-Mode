# Play together over Radmin

[Deutsch](RADMIN-DE.md) · [Installation](README-EN.md)

1. Install and open [Radmin VPN](https://www.radmin-vpn.com/) on every PC. The host creates a private network; guests join using the same network name and password. You can reuse an existing shared network. [Official help](https://www.radmin-vpn.com/help/).
2. Check that you can see each other online in Radmin. The host shares their **IPv4 address shown by Radmin**. Guests must use the host address, not their own address or the normal Wi-Fi address. Do not include private network passwords in the mod package.
3. Install the same mod test package on every PC. Open `Launch-Coop.cmd`. The host chooses **Host**; guests choose **Join** and enter the host IP without `:25200`.
4. Host and guests start their games through the launcher. The host presses Enter in their launcher console only after all guest game windows are open. This starts the server. Only the host selects the story/Continue.
5. Keep launcher consoles and garage windows open during the session. Each player chooses their own car in the garage, preferably between missions. Avoid gas stations.

## If you cannot connect

- Check that everyone is online in the same Radmin network, the host IP is correct and all PCs use the same mod build.
- The host must confirm server startup after guest game windows are open.
- The game uses **UDP 25200**. The garage sends guest selections to the host garage over **TCP 25211**, using the same host IP automatically.
- Windows Firewall must allow those connections over the Radmin network. If needed, the host can run `Enable-HostFirewall.cmd -FriendVpnAddress GUEST-RADMIN-IP` for the individual guest's Radmin IP. Use the **guest IP** for that firewall rule, not the host IP. This targeted step requires administrator permissions; run it only if needed. Its current console messages are German.
- Router port forwarding is not needed for this shared Radmin route. Do not add broad port rules.

If a game crashes or loading stops, report which client was affected and what happened; do not start extra servers alongside the current session. See [README-EN.md](README-EN.md) and `GAMEPLAY-STATUS.json` for build-specific limits. A 1–4 player limit in the launcher does not establish that four PCs have been tested successfully.
