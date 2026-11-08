"""Client fix for the post-race crash in the native MP leaderboard (NAECHSTE-BUILDS-2026-11-07.md).

Windows metadata 01:27:51 / 01:32:00: C0000005 at 90D5E1 `mov eax,[eax+20]` in the native
Career leaderboard builder 90D570, which our Story-LAN HUD (coop_hud_adapter) now reaches.
90D5D0 calls 866A60 (local racer). 866A60 returns NULL natively when the local player is
missing, the racer list is empty, the player is marked 0xBAADBAAD (freed) or 8635B0 finds no
racer with the player's id -- all plausible right after a race ends.

The adapter replaces only the CALL at 90D5D0:
- racer != NULL: return it unchanged; execution continues at 90D5D5 exactly as before.
- racer == NULL: drop our return address and jump to 90D87F, the native tail of the same
  function that frees the temporary list buffer ([esp+28..30], filled before 90D5D0) and falls
  into the native epilogue 90D89E. Only this frame's leaderboard build is skipped; no dummy
  racer, no invented data.
"""
import struct
from checkpoint_humans_adapter import Code

SITE, NATIVE = 0x90D5D0, 0x866A60
CONTINUE, NATIVE_TAIL = 0x90D5D5, 0x90D87F
SITE_BYTES = bytes.fromhex('e88b94f5ff')
TAIL_BYTES = bytes.fromhex('8b4c242cc1e906f6c10174138b5424308b4c2428528d44242c50e802bdb7005f5e5d5b8be55dc3')
CALLS, SKIPPED = 0, 4
CODE_SECTION, DATA_SECTION = b'.hudrcg', b'.hudrcs'


def absolute(c, op, address):
    c.emit(op)
    c.data += struct.pack('<I', address)


def make_code(base, stats):
    c = Code(base)
    absolute(c, 'ff05', stats + CALLS)        # inc [CALLS]
    c.branch('e8', NATIVE)                     # eax = local racer (thiscall, ECX unchanged by us)
    c.emit('85c0')                             # test eax,eax
    c.branch('0f84', 'skip')
    c.emit('c3')                               # racer present: back to 90D5D5
    c.label('skip')
    absolute(c, 'ff05', stats + SKIPPED)       # inc [SKIPPED]
    c.emit('83c404')                           # drop return address -> function body ESP
    c.branch('e9', NATIVE_TAIL)                # native buffer free + epilogue
    return c.finish()
