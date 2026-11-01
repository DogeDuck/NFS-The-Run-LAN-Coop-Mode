"""Scoped experiment: allow native NPC fill in two-human Story LAN races.

No global mode writes, synthetic racers or grid edits. Keeps native total-human
quota and the original spawn/profile functions. Scripted police are separate.
"""
import struct
from checkpoint_humans_adapter import Code, story_guard

SITE = 0x13D6556
ORIGINAL = bytes.fromhex('807c2412007419')
FILL, SKIP = 0x13D655D, 0x13D6576


def make_code(base, stats, preserve_solo=False):
    c = Code(base)
    def absolute(op, value):
        c.emit(op)
        c.data += struct.pack('<I', value)
    c.data += ORIGINAL[:5]
    c.emit('9c60')
    c.emit('807c243600')  # Native local flag+12, after36 saved bytes.
    c.branch('0f85', 'native')
    story_guard(c, 'native')
    c.emit('837c244002')  # Exactly two humans already created.
    c.branch('0f85', 'native')
    c.emit('80bbc305000000')
    c.branch('0f84', 'native')
    c.emit('8b83c805000083f8'+('02' if preserve_solo else '03'))
    c.branch('0f82', 'native')  # No underflow or pointless zero-AI case.
    c.emit('83f810')
    c.branch('0f87', 'native')
    c.emit('83e8'+('01' if preserve_solo else '02'))
    c.emit('8b7c244c85ff')
    c.branch('0f84', 'native')
    c.emit('8b4f288b772485f6')
    c.branch('0f84', 'native')
    c.emit('39f1')
    c.branch('0f82', 'native')
    c.emit('2bcef6c103')
    c.branch('0f85', 'native')
    c.emit('c1e90283f940')
    c.branch('0f87', 'native')
    c.emit('8b93c8050000')
    if preserve_solo:c.emit('42')  # One extra human must not displace an NPC.
    c.emit('3bca')
    c.branch('0f82', 'native')
    c.emit('8b7f4885ff')
    c.branch('0f84', 'native')
    c.emit('31f631d2')
    c.label('bits')
    c.emit('0fa337')
    c.branch('0f82', 'occupied')
    c.emit('42')
    c.label('occupied')
    c.emit('463bf1')
    c.branch('0f82', 'bits')
    c.emit('3bd0')
    c.branch('0f82', 'native')
    absolute('f0ff05', stats)
    absolute('a3', stats + 8)
    c.emit('619d')
    c.branch('e9', FILL)
    c.label('native')
    absolute('f0ff05', stats + 4)
    c.emit('619d')
    c.branch('0f84', SKIP)
    c.branch('e9', FILL)
    return c.finish()
