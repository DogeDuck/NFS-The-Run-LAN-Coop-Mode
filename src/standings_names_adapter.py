"""STANDINGS rows show the real LAN player name for human racers (Claude 15.11.2026).

User wish (15.11.): rows like "1  CoopHost", "2  Mia" instead of random names; AI keep their names.
Native leaderboard 90D570 (client DF9F7069, unchanged in R2/R3), per rank r: racer = 863290(r)
(racer list [28824F8]+3C..40, [racer+20] == r). Row name: 90D779 pushes [racer+80] (char*), 90D7CF CALL 890FD0
(thiscall, ECX = text buffer, RET 4) formats it; EDI = racer at that point.
Humans: ClientPlayerManager [2888F78], capacity [+8] (<= 0x40), table [+C0]; entry VT 254F020,
ID [+334] == slot, bot byte [+260] == 0, name char* [+10] (live 09.11.: CoopGuest / CoopHost).
Racer ID [racer+10] (Codex hud-name-paths, team-finish adapters).
Patch: CALL 890FD0 at 90D7CF -> stub. In connected LAN story, if [racer+10] maps to a human ClientPlayer with a
non-empty name, the pushed name argument is replaced by that player's name; otherwise native. Rank numbers and
ordering stay native (setupPositions).
"""
import struct
from checkpoint_humans_adapter import Code
import coop_hud_adapter as hud

SITE, TARGET = 0x90D7CF, 0x890FD0
PLAYERS, PLAYER_VTABLE = 0x2888F78, 0x254F020
CALLS, NAMED = 0, 4
DATA_SIZE = 0x10


def call_patch(site, target):
    return b'\xe8' + struct.pack('<i', target - site - 5)


def make_code(base, data):
    c = Code(base)
    def absolute(op, value): c.emit(op); c.data += struct.pack('<I', value)
    c.emit('9c60')                                   # pushfd; pushad -> name argument at [esp+28]
    absolute('ff05', data + CALLS)
    hud.guard(c)
    c.emit('85ff'); c.branch('0f84', 'native')       # racer (EDI)
    c.emit('8b4710')                                 # eax = racer ID
    absolute('8b15', PLAYERS); c.emit('85d2'); c.branch('0f84', 'native')
    c.emit('8b4a08'); c.emit('83f940'); c.branch('0f87', 'native')   # capacity <= 0x40
    c.emit('39c8'); c.branch('0f83', 'native')       # ID < capacity
    c.emit('8b92c0000000'); c.emit('85d2'); c.branch('0f84', 'native')
    c.emit('8b1482'); c.emit('85d2'); c.branch('0f84', 'native')   # edx = table[ID]
    c.emit('813a'); c.data += struct.pack('<I', PLAYER_VTABLE); c.branch('0f85', 'native')
    c.emit('398234030000'); c.branch('0f85', 'native')             # ID matches slot
    c.emit('80ba6002000000'); c.branch('0f85', 'native')           # human (bot byte 0)
    c.emit('8b5210'); c.emit('85d2'); c.branch('0f84', 'native')   # name char*
    c.emit('803a00'); c.branch('0f84', 'native')                   # non-empty
    c.emit('89542428')                               # replace pushed name
    absolute('ff05', data + NAMED)
    c.label('native'); c.emit('619d'); c.branch('e9', TARGET)
    return c.finish()
