"""Server adapter: the HOST's difficulty (launcher) is the AI difficulty, not the last client message.

Native: every client sends its profile difficulty (84A6B0 -> message 0x35288669/0x1B56CBD9, value +38,
send EDA970). The server stores the value of whatever message arrives last:
  site 1  127E712  mov eax,[edi+38]; mov [esi+24],eax      (6 bytes, resume 127E718)
  site 2  13FE3A6  mov eax,[edx+38]; mov [ecx+5A8],eax     (9 bytes, resume 13FE3AF)
So with 2-4 players a guest's profile can silently override the host's AI difficulty.

Adapter (JMP over each site): once, read env THERUN_DIFFICULTY of the server process via its import
GetEnvironmentVariableA (IAT 0x2A8B850, FXSAVE around the call). Exactly one char '0'..'3'
(RaceAIDifficulty 0 Easy, 1 Normal, 2 Hard, 3 Expert/Extreme) -> that value is stored instead of the
message value; anything else -> exact native store forever. All registers except the stored EAX
(native also loads EAX) and EFLAGS are preserved. Client-local caches stay native (own profile).
"""
import struct
from checkpoint_humans_adapter import Code

GETENV_IAT = 0x2A8B850
SITES = (('ai_manager', 0x127E712, bytes.fromhex('8b4738894624'), 0x127E718, '8b4738', '894624'),
         ('race_manager', 0x13FE3A6, bytes.fromhex('8b42388981a8050000'), 0x13FE3AF, '8b4238', '8981a8050000'))
CALLS1, CALLS2, FORCED, LAST_NATIVE, STATE, VALUE, ENVNAME, ENVBUF = 0, 4, 8, 12, 16, 20, 0x20, 0x40
ENV = b'THERUN_DIFFICULTY\0'
STATS_SIZE = 0x60
UNRESOLVED, NATIVE, FORCE = 0, 1, 2


def stats_init():
    return b'\0' * ENVNAME + ENV + b'\0' * (STATS_SIZE - ENVNAME - len(ENV))


def make_code(base, stats, getenv_iat=GETENV_IAT):
    """Returns (code, {site name: entry})."""
    c = Code(base)
    a = lambda op, v: (c.emit(op), c.data.extend(struct.pack('<I', v)))
    for index, (name, site, original, resume, load, store) in enumerate(SITES):
        c.label(name)
        c.emit(load)                                            # eax = native message value
        a('ff05', stats + (CALLS1 if index == 0 else CALLS2))
        a('a3', stats + LAST_NATIVE)
        c.branch('e8', 'resolve')                               # keeps every register except flags
        a('833d', stats + STATE); c.emit('02'); c.branch('0f85', name + '_store')
        a('a1', stats + VALUE); a('ff05', stats + FORCED)
        c.label(name + '_store')
        c.emit(store); c.branch('e9', resume)
    # resolve: once, env -> STATE/VALUE. Preserves all registers.
    c.label('resolve')
    a('833d', stats + STATE); c.emit('00'); c.branch('0f85', 'resolved')
    c.emit('60')                                                # pushad
    c.emit('89e581ec1002000083e4f00fae0424')                    # ebp = esp; aligned fxsave
    c.emit('6a10'); a('68', stats + ENVBUF); a('68', stats + ENVNAME)
    a('ff15', getenv_iat)                                       # eax = length
    a('c705', stats + STATE); c.data += struct.pack('<I', NATIVE)
    c.emit('83f801'); c.branch('0f85', 'env_done')
    a('0fb605', stats + ENVBUF)                                 # movzx eax, byte [buf]
    c.emit('2c30'); c.emit('3c03'); c.branch('0f87', 'env_done')   # '0'..'3'
    a('a3', stats + VALUE)
    a('c705', stats + STATE); c.data += struct.pack('<I', FORCE)
    c.label('env_done')
    c.emit('0fae0c2489ec61')                                    # fxrstor; esp = ebp; popad
    c.label('resolved')
    c.emit('c3')
    code = c.finish()
    return code, {name: c.labels[name] for name, *_ in SITES}


def jmp_patch(site, length, target):
    return b'\xe9' + struct.pack('<i', target - site - 5) + b'\x90' * (length - 5)
