"""Targeted 1.51 orphan actor-spawner release; native calls on the game thread."""
import struct
import uuid
from checkpoint_humans_adapter import Code
SITE, TARGET = 0xEF21D7, 0xEF1B10
# Full EF0EE0 cleanup also mutates actor component lists. Do not apply it to
# live player cars: the first prototype crashed during component enumeration.
MANAGER_CONTAINS = 0xEDF7B0
MANAGER_REMOVE = 0xEEE500
GUID = uuid.UUID('6f244028-7f50-4db1-b7c1-4ce150b0b77d')
OWNERS = [uuid.UUID(x) for x in ('44ba2a91-e329-401e-a766-5c68c3a572dc', '574de6e2-3fa8-45d4-a51b-c324b085dc34')]


def make_code(base, stats, runtime_lanes=False):
    c = Code(base)
    def absolute(op, value):
        c.emit(op); c.data += struct.pack('<I', value)
    def match_guid(register, guid, fail):
        for i, word in enumerate(struct.unpack('<4I', guid.bytes_le)):
            c.emit('81' + register + bytes([0xF0+4*i]).hex())
            c.data += struct.pack('<I', word)
            c.branch('0f85', fail)
    c.emit('9c60')
    # Only an actual connected LAN client and current challenge1.51.
    absolute('a1', 0x2888F7C)
    c.emit('85c0'); c.branch('0f84', 'fallback')
    c.emit('80780800'); c.branch('0f85', 'fallback')
    c.emit('83b8a400000003'); c.branch('0f85', 'fallback')
    absolute('a1', 0x28824E8)
    c.emit('85c0'); c.branch('0f84', 'fallback')
    c.emit('8b401085c0'); c.branch('0f84', 'fallback')
    match_guid('78', GUID, 'fallback')  # CMP [EAX-16+offset], immediate
    # ECX was preserved by pushad at ESP+24.
    c.emit('8b742418813ea0065902'); c.branch('0f85', 'fallback')
    c.emit('8b561485d2'); c.branch('0f84', 'fallback')
    match_guid('7a', OWNERS[0], 'second_owner')
    c.branch('e9', 'matched')
    c.label('second_owner')
    match_guid('7a', OWNERS[1], 'fallback')
    c.label('matched')
    absolute('ff05', stats+8)
    # Preserve FPU/SIMD state across the additional native cleanup/teleport.
    c.emit('89e581ec2002000083e4f00fae0424')
    c.emit('f6866007000004'); c.branch('0f84', 'after_release')
    absolute('8b0d', 0x288B990)
    c.emit('85c9'); c.branch('0f84', 'done')
    c.emit('56'); c.branch('e8', MANAGER_CONTAINS)
    c.emit('84c0'); c.branch('0f84', 'unregistered')
    absolute('8b0d', 0x288B990)
    c.emit('56'); c.branch('e8', MANAGER_REMOVE)
    c.label('unregistered')
    c.emit('80a660070000f9')  # native registration bits only; no actor list edits
    # Release physics animation for the sole bound vehicle, leaving all visual
    # and input components owned by that live vehicle intact.
    c.emit('8b465c8b566029c283fa04'); c.branch('0f85', 'after_release')
    c.emit('8b38813f20d25402'); c.branch('0f85', 'after_release')
    c.emit('8b8fe400000085c9'); c.branch('0f84', 'after_release')
    c.emit('813950014002'); c.branch('0f85', 'after_release')
    c.emit('6a00'); c.branch('e8', 0x69D420)
    absolute('ff05', stats+4)
    c.label('after_release')
    # Teleport only this client's owned human car, once. Other actors use native cleanup.
    absolute('a1', 0x2888F78)
    c.emit('85c0'); c.branch('0f84', 'done')
    c.emit('8b80bc00000085c0'); c.branch('0f84', 'done')
    c.emit('8bb81803000085ff'); c.branch('0f84', 'done')
    c.emit('813f20d25402'); c.branch('0f85', 'done')
    c.emit('8b465c8b566029c283fa04'); c.branch('0f85', 'done')
    c.emit('3938'); c.branch('0f85', 'done')
    # Release a native AI handoff whenever it is re-enabled on this local car.
    c.emit('8b477c85c0'); c.branch('0f84', 'after_ai')
    c.emit('8b400885c0'); c.branch('0f84', 'after_ai')
    c.emit('813818f05802'); c.branch('0f85', 'after_ai')
    c.emit('80782000'); c.branch('0f84', 'after_ai')
    c.emit('6a006a006a0089f9'); c.branch('e8', 0xF29820)
    absolute('ff05', stats+16)
    c.label('after_ai')
    # A full event retry creates a different vehicle. Recover each new local
    # entity once, rather than consuming a single process-wide armed flag.
    absolute('393d', stats+24); c.branch('0f84', 'done')
    c.emit('8bb7e400000085f6'); c.branch('0f84', 'done')
    c.emit('813e50014002'); c.branch('0f85', 'done')
    c.emit('6a0089f1'); c.branch('e8', 0x69D420)
    c.emit('6a006a00')
    for address in (stats+0x150, stats+0x140): absolute('68', address)
    if runtime_lanes:
        absolute('a1', 0x2888F78)
        c.emit('8b80bc0000008b803403000083e001c1e00705')
        c.data += struct.pack('<I', stats+0x100)
        c.emit('50')
    else:
        absolute('68', stats+0x100)
    c.emit('89f9'); c.branch('e8', 0xF1A850)
    absolute('893d', stats+24)
    absolute('c705', stats); c.emit('00000000')
    absolute('ff05', stats+12)
    c.label('done')
    c.emit('0fae0c2489ec619dc20400')
    c.label('fallback')
    c.emit('619d'); c.branch('e9', TARGET)
    return c.finish()
