"""Remote player cars get their lights (Claude 15.11.2026). User: "nur der Client hat Lichter, der Mitspieler nicht".

Live measurement (vehicle_lights_probe.py, frida_write_watch.py, session local-checkpoint-20261114-235140):
vehicle input block V+0x300, bytes +B5 / +B6 (V+3B5/3B6) = 1 on the own car, 0 on the other human's car in both
clients. Writers: 68FF00 resets the block (68FFE3 +B5 = 0, 68FFEC +B6 = 0) every frame; only for locally driven
cars the input update 69AA90 then sets +B5 (69B064) and +B6 (69B08C). Network cars only get the reset.
Patch: the epilogue of 68FF00 (690198: movss [ecx+2B8],xmm0; pop ebx; ret = 10 bytes) jumps to a stub that runs
those instructions, then (connected LAN story only) checks whether V = ECX-0x300 is the vehicle of another human
ClientPlayer (table [[2888F78]+C0], VT 254F020, bot byte +260 == 0, not the local player [mgr+BC],
entity [p+318] VT 254D220, vehicle [entity+E4] == V) and then writes the configured light bytes (default 1/1).
The local car and AI cars are untouched; flags, registers and XMM are preserved.
Only the 8-byte movss at 690198 is replaced; the stub returns to the native 'pop ebx; ret' at 6901A0, so a thread
suspended there during installation stays safe.
"""
import struct
from checkpoint_humans_adapter import Code
import coop_hud_adapter as hud

SITE, RESUME = 0x690198, 0x6901A0      # only the 8-byte movss is replaced; 'pop ebx; ret' stays native
ORIGINAL = bytes.fromhex('f30f1181b8020000')
PLAYERS, PLAYER_VT, ENTITY_VT, VEHICLE_VT = 0x2888F78, 0x254F020, 0x254D220, 0x2400150
BLOCK = 0x300
CALLS, LIT, B5_VALUE, B6_VALUE = 0x00, 0x04, 0x08, 0x09
DATA_SIZE = 0x10


def data_init(b5=1, b6=1):
    d = bytearray(DATA_SIZE); d[B5_VALUE] = b5; d[B6_VALUE] = b6
    return bytes(d)


def site_patch(stub):
    return b'\xe9' + struct.pack('<i', stub - SITE - 5) + b'\x90' * 3


def make_code(base, data):
    c = Code(base)
    def absolute(op, value): c.emit(op); c.data += struct.pack('<I', value)
    c.emit('f30f1181b8020000')                         # original movss [ecx+2B8],xmm0
    c.emit('9c60')
    absolute('ff05', data + CALLS)
    hud.guard(c)                                       # clobbers eax only
    c.emit('8db900fdffff')                             # lea edi,[ecx-300h] = V
    c.emit('813f'); c.data += struct.pack('<I', VEHICLE_VT); c.branch('0f85', 'native')
    absolute('8b15', PLAYERS); c.emit('85d2'); c.branch('0f84', 'native')   # edx = mgr
    c.emit('8bb2bc000000')                             # esi = local player
    c.emit('8b6a08'); c.emit('83fd40'); c.branch('0f87', 'native')          # ebp = capacity <= 64
    c.emit('8b92c0000000'); c.emit('85d2'); c.branch('0f84', 'native')     # edx = table
    c.emit('31db')                                     # ebx = i
    c.label('loop'); c.emit('39eb'); c.branch('0f83', 'native')
    c.emit('8b049a'); c.emit('85c0'); c.branch('0f84', 'next')             # eax = player
    c.emit('39f0'); c.branch('0f84', 'next')           # local player
    c.emit('8138'); c.data += struct.pack('<I', PLAYER_VT); c.branch('0f85', 'next')
    c.emit('80b86002000000'); c.branch('0f85', 'next') # bot
    c.emit('8b8018030000'); c.emit('85c0'); c.branch('0f84', 'next')       # entity
    c.emit('8138'); c.data += struct.pack('<I', ENTITY_VT); c.branch('0f85', 'next')
    c.emit('3bb8e4000000'); c.branch('0f84', 'lit')    # [entity+E4] == V
    c.label('next'); c.emit('43'); c.branch('e9', 'loop')
    c.label('lit')
    absolute('a0', data + B5_VALUE); c.emit('8881b5000000')                 # [ecx+B5] = b5
    absolute('a0', data + B6_VALUE); c.emit('8881b6000000')                 # [ecx+B6] = b6
    absolute('ff05', data + LIT)
    c.label('native'); c.emit('619d'); c.branch('e9', RESUME)   # popad; popfd; back to native 'pop ebx; ret'
    return c.finish()
