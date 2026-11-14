"""HOST-controlled QTE input: the HOST's QTE/HUD button mask also counts on the GAST (Claude 15.11.2026).

User goal: one player presses for all during QTEs. Native (client DF9F7069, unchanged in R2/R3):
8D2C40 packs the per-frame HUD input mask (digital buttons + stick directions from 11C7C90/11C7C20) and passes a
pointer to it at 8D2FF5: CALL 57B5B0 (thiscall ECX = [ESI+150] UI input, arg = uint* mask, RET 4). 57B5B0 maps the
bits to UI concepts; the QTE context button reads those (941FE6/942086 report success/failure).
Patch: that CALL -> stub. Only in connected LAN story while the challenge is out-of-car (QTE/OOC route, the same
gate as the fail guard). On every client the stub publishes the local mask (SEND_MASK, SEND_SEQ++). On the exact
GUEST role it additionally ORs the received mask (RECV_MASK) into the native mask if RECV_TICK is fresh
(GetTickCount within FRESH_MS). Transport is outside the game: a helper copies HOST SEND_MASK -> GAST RECV_MASK
(locally via process memory, between PCs via UDP). The GAST's own buttons still work (OR, not replace).
Analog stick magnitudes (57B4B0) are not mirrored, only the direction bits contained in the mask.
"""
import struct
from checkpoint_humans_adapter import Code
import coop_hud_adapter as hud
from qte_hud_scope_adapter import challenge_route

SITE, TARGET = 0x8D2FF5, 0x57B5B0
GETENV_IAT, GETTICK_IAT = 0x2A8B850, 0x2A8B8E4
CALLS, ROLE, RESOLVES, NAME = 0x00, 0x08, 0x0C, 0x20
SEND_MASK, SEND_SEQ, RECV_MASK, RECV_TICK, MERGED, OOC_FRAMES = 0x40, 0x44, 0x48, 0x4C, 0x50, 0x54
DATA_SIZE = 0x60
FRESH_MS = 300
ENV_NAME = b'THERUN_COOP_ROLE\0'
ROLE_OTHER, ROLE_GUEST = 1, 2


def data_init(role=0):
    d = bytearray(DATA_SIZE)
    d[NAME:NAME + len(ENV_NAME)] = ENV_NAME
    struct.pack_into('<I', d, ROLE, role)
    return bytes(d)


def call_patch(site=SITE, target=TARGET):
    return b'\xe8' + struct.pack('<i', target - site - 5)


def make_code(base, data, getenv_iat=GETENV_IAT, gettick_iat=GETTICK_IAT):
    c = Code(base)
    def absolute(op, value): c.emit(op); c.data += struct.pack('<I', value)
    c.emit('9c60bb'); c.data += struct.pack('<I', data)          # pushfd; pushad; ebx = data
    c.emit('ff03')                                               # calls++
    hud.guard(c)
    challenge_route(c, 'ooc', 'native')
    c.label('ooc')
    c.emit('8b742428'); c.emit('85f6'); c.branch('0f84', 'native')   # esi = mask ptr ([esp+28h])
    c.emit('8b0e'); c.emit('894b40'); c.emit('ff4344'); c.emit('ff4354')   # publish mask, seq++, ooc frames++
    # Exact GUEST role (same reader as qte_guest_fail_guard_adapter): getenv once, fail open for anything else.
    c.emit('837b0800'); c.branch('0f85', 'have_role')
    c.emit('81ec300200008d6c241f83e5f00fae45008d04246a10508d432050')
    absolute('ff15', getenv_iat)
    c.emit('ff430cc7430801000000')
    c.emit('83f805'); c.branch('0f85', 'role_done')
    c.emit('8b042425dfdfdfdf3d47554553'); c.branch('0f85', 'role_done')
    c.emit('8a44240424df3c54'); c.branch('0f85', 'role_done')
    c.emit('c7430802000000')
    c.label('role_done'); c.emit('0fae4d0081c430020000')
    c.label('have_role'); c.emit('837b0802'); c.branch('0f85', 'native')
    absolute('ff15', gettick_iat)                                # eax = now (esi/ebx preserved by the import)
    c.emit('2b434c'); c.emit('3d'); c.data += struct.pack('<I', FRESH_MS); c.branch('0f87', 'native')
    c.emit('8b4b48'); c.emit('090e'); c.emit('ff4350')           # *mask |= recv; merged++
    c.label('native'); c.emit('619d'); c.branch('e9', TARGET)
    return c.finish()
