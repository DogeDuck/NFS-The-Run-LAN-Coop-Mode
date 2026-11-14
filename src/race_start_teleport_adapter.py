"""Server fix (Claude 12.11.2026): race-start teleport keeps extra humans next to the first human.

Live finding (12.2, outputs/srv-sendtp.out.txt, watchphys-*): at race start the server race manager loop 13D4530
teleports every racer to the TeleportGrid entry with the SAME index as its start-grid slot
(13D4645: CALL 13E0130 ServerTeleportEntity::teleport(player, 0, 0.0)). The coop spawn adapter puts the extra human
on a reserved slot behind the solo roster; in the authored TeleportGrid that entry points ~275 m back. The client of
whoever did NOT trigger the load therefore jumps back when the race starts.

Hook: the CALL 12E9BF0 (send teleport message, arg1 = target LinearTransform*) at 13E0221 inside 13E0130.
Only when 13E0130 was called from that race-start loop (return 13D464A):
  * the first human of a pass keeps his target; it is copied to the anchor buffer,
  * every further human k=1..3 of the same pass gets anchor translation - forward * 8k (same orientation),
AI racers and every other teleport (resets, checkpoints, scripts) are untouched. A pass ends when the loop's slot
index does not increase. Registers/flags preserved; XMM0-2 are clobbered only at a call boundary (volatile).
"""
import struct
from checkpoint_humans_adapter import Code

SITE, TARGET = 0x13E0221, 0x12E9BF0
LOOP_RETURN = 0x13D464A
MANAGER = 0x28E5C90
# RW state layout
LAST_SLOT, ANCHOR_VALID, EXTRA_K, EIGHT, APPLIED, ANCHORS = 0x00, 0x04, 0x08, 0x0C, 0x10, 0x14
ANCHOR, BUF = 0x40, 0x80
STATS_SIZE = 0xC0


def stats_init():
    data = bytearray(STATS_SIZE)
    struct.pack_into('<I', data, LAST_SLOT, 0xFFFFFFFF)
    struct.pack_into('<f', data, EIGHT, 8.0)
    return bytes(data)


def make_code(base, stats):
    c = Code(base)
    a = lambda off: struct.pack('<I', stats + off).hex()
    c.emit('9c60fc')                                  # pushfd; pushad; cld   (arg1 now at [esp+28h])
    c.emit('817d04' + struct.pack('<I', LOOP_RETURN).hex()); c.branch('0f85', 'done')  # only the race-start loop
    c.emit('8b750885f6'); c.branch('0f84', 'done')     # esi = player ([ebp+8] of 13E0130)
    c.emit('8b86e4020000')                           # eax = player id
    c.emit('8b15' + struct.pack('<I', MANAGER).hex() + '85d2'); c.branch('0f84', 'done')
    c.emit('8b8a6c050000' '8b9270050000')             # ecx = racers begin, edx = end
    c.label('scan')
    c.emit('39d1'); c.branch('0f83', 'done')
    c.emit('8b1983c10485db'); c.branch('0f84', 'scan')
    c.emit('394310'); c.branch('0f85', 'scan')        # racer id == player id
    c.emit('8b7b344f')                               # edi = grid slot (racer+34 is slot+1)
    c.emit('3b3d' + a(LAST_SLOT)); c.branch('0f87', 'same_pass')
    c.emit('c705' + a(ANCHOR_VALID) + '00000000' 'c705' + a(EXTRA_K) + '00000000')
    c.label('same_pass')
    c.emit('893d' + a(LAST_SLOT))
    c.emit('837b1400'); c.branch('0f85', 'done')     # driver kind 0 = human
    c.emit('8b74242885f6'); c.branch('0f84', 'done') # esi = target transform*
    c.emit('833d' + a(ANCHOR_VALID) + '00'); c.branch('0f85', 'extra')
    c.emit('bf' + a(ANCHOR) + 'b910000000f3a5')        # copy 64 bytes -> anchor
    c.emit('c705' + a(ANCHOR_VALID) + '01000000' 'ff05' + a(ANCHORS))
    c.branch('e9', 'done')
    c.label('extra')
    c.emit('ff05' + a(EXTRA_K) + '833d' + a(EXTRA_K) + '03'); c.branch('0f87', 'done')
    c.emit('be' + a(ANCHOR) + 'bf' + a(BUF) + 'b910000000f3a5')  # buf = anchor
    c.emit('f30f2a05' + a(EXTRA_K))                   # cvtsi2ss xmm0, k
    c.emit('f30f5905' + a(EIGHT))                     # mulss xmm0, 8.0
    c.emit('0fc6c000')                                # shufps xmm0, xmm0, 0
    c.emit('0f100d' + a(BUF + 0x20))                  # movups xmm1, forward
    c.emit('0f59c8')                                  # mulps xmm1, xmm0
    c.emit('0f1015' + a(BUF + 0x30))                  # movups xmm2, translation
    c.emit('0f5cd1')                                  # subps xmm2, xmm1
    c.emit('0f1115' + a(BUF + 0x30))                  # movups translation, xmm2
    c.emit('b8' + a(BUF) + '89442428')                # arg1 = &buf
    c.emit('ff05' + a(APPLIED))
    c.label('done')
    c.emit('619d')                                    # popad; popfd
    c.branch('e9', TARGET)
    return c.finish()
