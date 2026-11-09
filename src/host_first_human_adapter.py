"""Server adapter: the HOST becomes the "first human" (story player) instead of list order.

132AC60 (thiscall ServerPlayerManager, no args, plain RET) returns the first non-bot player of
[mgr+78..7C]. 44 server call sites use it whenever a story event carries no player: grid builder
13D64F3 (story-player message), VehicleInteraction 13E2AE8 (10.5 police car), challenge states
13E4150, battle finish 13E0BA2 ... Live 09.11.: list order was [CoopGuest, CoopHost], so the GUEST
always became the story player: only his client had the character/vehicle at the scene (world
streaming + QTE input), the host saw fog and his QTE input was ignored.

Adapter (JMP over the first 6 bytes of 132AC60):
  * once: read env THERUN_HOST_NAME of the server process via its import GetEnvironmentVariableA
    (IAT 0x2A8B850), FXSAVE around the call. Unset/empty/too long -> exact native behaviour forever.
  * return the non-bot player whose name string ([player+10] -> char*) equals that name;
  * otherwise exactly the native result (first non-bot player or NULL).
Works for 2-4 players (one host). Registers: EAX result; ECX/EDX volatile like native; EBX/ESI/EDI/EBP,
ESP and EFLAGS-independent callers unchanged. No player list, bot flag or name is written.
"""
import struct
from checkpoint_humans_adapter import Code

SITE, RESUME = 0x132AC60, 0x132AC66
SITE_BYTES = bytes.fromhex('8b517c8b4978')
GETENV_IAT = 0x2A8B850
NAME_OFFSET, BOT_OFFSET = 0x10, 0x260
CALLS, HOST_HITS, NATIVE, ROLE, ENVNAME, HOSTNAME = 0, 4, 8, 12, 0x20, 0x40
NAME_MAX = 0x40
ENV = b'THERUN_HOST_NAME\0'
STATS_SIZE = 0x80


def stats_init():
    return b'\0' * ENVNAME + ENV + b'\0' * (STATS_SIZE - ENVNAME - len(ENV))


def make_code(base, stats, getenv_iat=GETENV_IAT):
    c = Code(base)
    imm = lambda v: struct.pack('<I', v)
    c.emit('535657')                                     # push ebx, esi, edi
    c.emit('89ce')                                       # esi = manager
    c.emit('bb'); c.data += imm(stats)
    c.emit('ff03')                                       # calls++
    c.emit('837b0c00'); c.branch('0f85', 'have_role')
    c.emit('81ec300200008d7c241f83e7f00fae07')           # sub esp,230; edi = aligned; fxsave [edi]
    c.emit('6a' + bytes([NAME_MAX]).hex())               # push size
    c.emit('8d4340' + '50')                              # lea eax,[ebx+HOSTNAME]; push eax
    c.emit('8d4320' + '50')                              # lea eax,[ebx+ENVNAME]; push eax
    c.emit('ff15'); c.data += imm(getenv_iat)            # stdcall, eax = length (0 = unset)
    c.emit('c7430c01000000')                             # role = native
    c.emit('85c0'); c.branch('0f84', 'role_done')
    c.emit('83f83f'); c.branch('0f87', 'role_done')      # too long / truncated -> native
    c.emit('c7430c02000000')                             # role = host name known
    c.label('role_done')
    c.emit('0fae0f81c430020000')                         # fxrstor [edi]; add esp,230
    c.label('have_role')
    c.emit('837b0c02'); c.branch('0f85', 'native')
    c.emit('8b4e788b567c')                               # ecx = begin, edx = end
    c.label('scan')
    c.emit('39d1'); c.branch('0f83', 'native')
    c.emit('8b3983c10485ff'); c.branch('0f84', 'scan')   # edi = player; next
    c.emit('80bf' + struct.pack('<I', BOT_OFFSET).hex() + '00'); c.branch('0f85', 'scan')
    c.emit('8b4710'); c.emit('85c0'); c.branch('0f84', 'scan')   # eax = name pointer
    c.emit('5152')                                       # keep cursor/end
    c.emit('8d5340')                                     # edx = host name
    c.label('cmp')
    c.emit('8a08'); c.emit('3a0a'); c.branch('0f85', 'differ')
    c.emit('84c9'); c.branch('0f84', 'match')
    c.emit('4042'); c.branch('e9', 'cmp')
    c.label('differ'); c.emit('5a59'); c.branch('e9', 'scan')
    c.label('match'); c.emit('5a59')
    c.emit('89f8'); c.emit('ff4304'); c.branch('e9', 'out')
    c.label('native')                                    # exact native rule: first non-bot or NULL
    c.emit('ff4308')
    c.emit('8b567c8b4e78')
    c.label('nloop')
    c.emit('39d1'); c.branch('0f84', 'none')
    c.emit('8b0180b8' + struct.pack('<I', BOT_OFFSET).hex() + '00'); c.branch('0f84', 'out')
    c.emit('83c104'); c.branch('e9', 'nloop')
    c.label('none'); c.emit('31c0')
    c.label('out'); c.emit('5f5e5bc3')
    return c.finish()
