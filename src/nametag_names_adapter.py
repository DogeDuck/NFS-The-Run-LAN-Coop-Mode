"""Overhead nametags show the real player name instead of the race position in LAN story (Claude 15.11.2026).

User wish: above the other player's car show the player name, not a position number.
Native (client DF9F7069, unchanged in R2/R3):
  904240 per-frame nametag pass over the ClientPlayerManager players ([2888F78]+9C..A0).
  Mode [288239C]+4: 2 (story) -> state 3, 3 -> state 2, else UI option (hash C37B9249) == 2 -> state 1.
  Call 9024C0(player, state, position, health, isLookedAt):
    state 1 = NAMETAG: sprintf(buf, "%c%s", 0x3F, [player+0x10]) -> name text (player+0x10 = char* name,
              live-read 09.11.: [CoopGuest, CoopHost]); states 2/3 = POSITION ordinal; 4 = health bar.
  GFx widgetnametag (UI.sb) has the matching STATE_NAMETAG / STATE_POSITION / STATE_HEALTH frames.
Patch: the story branch 'mov dword [esp+0C],3' at 90426E (8 bytes) becomes CALL stub + 3x NOP.
The stub writes 3 natively and 1 (name) only in connected LAN story (coop_hud_adapter.guard).
Nothing else changes; the native position branch, health bar and UI option path stay intact.
"""
import struct
from checkpoint_humans_adapter import Code
import coop_hud_adapter as hud

SITE = 0x90426E
ORIGINAL = bytes.fromhex('c744240c03000000')       # mov dword [esp+0C], 3
RESUME = SITE + 8
STATE_POSITION, STATE_NAME = 3, 1
CALLS, NAMED = 0, 4
DATA_SIZE = 0x10


def make_code(base, data):
    c = Code(base)
    c.emit('9c60')                                   # pushfd; pushad (36 bytes) + return address = 40
    c.emit('c7442434'); c.data += struct.pack('<I', STATE_POSITION)
    c.emit('ff05'); c.data += struct.pack('<I', data + CALLS)
    hud.guard(c)                                     # connected LAN + story mode, else native
    c.emit('c7442434'); c.data += struct.pack('<I', STATE_NAME)
    c.emit('ff05'); c.data += struct.pack('<I', data + NAMED)
    c.label('native'); c.emit('619dc3')
    return c.finish()


def site_patch(stub):
    return b'\xe8' + struct.pack('<i', stub - SITE - 5) + b'\x90\x90\x90'
