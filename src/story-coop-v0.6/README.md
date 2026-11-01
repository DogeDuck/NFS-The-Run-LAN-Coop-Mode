# v0.6 TEST client team-result source

Requires Python3 and your own supported v0.5 patched game executable (SHA2562cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249).

python build_client.py --source "YOUR_V05_CLIENT.exe" --output "client-team-test.exe"

Expected output SHA25695ba75bb168b2ffc38c4539e2287d8be31dcc55d2001d53c7c7a60696c839f14.
Builds a separate file only. No game executable is distributed. Server patches remain those of v0.5.

The mode0 Story finish-time/rank getters use the first real finished human, with two non-bot players validated from the current client table on every call. Native win thresholds remain intact. Unknown rosters and solo play fall back to native behaviour. This is not a general replacement for scripted failures, arrests, QTE endings or all progression conditions. Gameplay validation of the dynamic variant is still limited; shared overtaken HUD is not included.
