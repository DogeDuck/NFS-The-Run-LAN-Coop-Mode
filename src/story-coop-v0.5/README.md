# v0.5 native server changes

Build with Python on Windows from your own v0.4 NFSTR_Server.exe, SHA25622f1604cc40643dbcb18154cda3da627a63f0b34a4dfdfd7631ad99c9a81b768:

    python build_server.py PATH_TO_V04_SERVER NEW_OUTPUT_FILE

Output SHA256:4afb76c21d08439778dba038ad787618f752aa3c639a18a07a5b1672c0263c9d.
The build refuses other baselines and never overwrites an existing output file.

The server patch retains the v0.4 checkpoint/reset baseline and adds the inseparable AI gate/quota pair, followed by two spawn adapters. RX code and RW session state use separate PE sections. Native functions execute on their original game thread. The explicit race GUID list excludes Stage1. Source-entity ownership and grid occupancy remain native; the second initial human pose is offset8m along negative authored forward. One-shot arms avoid repositioning later garage swaps. Additional races, resets and transitions still require in-game testing.

Only3.5 was confirmed for the new spawn mechanism. The complete persistent package was checked offline, not validated as a complete campaign. The experimental garage, pause and newer team-result work is intentionally absent.
