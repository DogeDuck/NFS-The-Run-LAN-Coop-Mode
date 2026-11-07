"""Scoped mode0 team-finish experiment, using the real native finish order.

Only substitute a verified human ID in two native Story result getter calls.
Native finish-time and winning-rank conditions remain intact. No fabricated
finish record, win event, teleport or global rank/UI override. Current-event
GUID and exactly two externally verified distinct human IDs are mandatory.
"""
import struct
import uuid
from checkpoint_humans_adapter import Code

SPECS = ((0x99128D, 0x802000), (0x9912A4, 0x802030))


def make_code(base, stats, target, challenge, humans):
    if target not in {native for _, native in SPECS}:
        raise ValueError('Unsupported native team getter')
    if len(humans) != 2 or len(set(humans)) != 2 or any(type(x) is not int or not 0 <= x < 64 for x in humans):
        raise ValueError('Two verified human IDs required')
    guid = uuid.UUID(str(challenge))
    c = Code(base)
    def absolute(op, value):
        c.emit(op)
        c.data += struct.pack('<I', value)
    c.emit('9c60')
    absolute('a1', 0x2888F7C)
    c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('80780800'); c.branch('0f85', 'native')
    c.emit('83b8a400000003'); c.branch('0f85', 'native')
    absolute('a1', 0x28824E8)
    c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('8b401085c0'); c.branch('0f84', 'native')
    for index, word in enumerate(struct.unpack('<4I', guid.bytes_le)):
        c.emit('8178'+bytes([0xF0+4*index]).hex())
        c.data += struct.pack('<I', word)
        c.branch('0f85', 'native')
    # Original argument must also be one of the verified humans.
    c.emit('8b4424283d'); c.data += struct.pack('<I', humans[0])
    c.branch('0f84', 'order')
    c.emit('3d'); c.data += struct.pack('<I', humans[1])
    c.branch('0f85', 'native')
    c.label('order')
    c.emit('8b4c24188b71708b797439f7')
    c.branch('0f86', 'native')
    c.emit('89f82bc6a907000000'); c.branch('0f85', 'native')
    c.emit('89f82bc63d00020000'); c.branch('0f87', 'native')
    c.label('scan')
    c.emit('8b063d'); c.data += struct.pack('<I', humans[0])
    c.branch('0f84', 'human')
    c.emit('3d'); c.data += struct.pack('<I', humans[1])
    c.branch('0f84', 'human')
    c.emit('83c6083bf7'); c.branch('0f82', 'scan')
    c.branch('e9', 'native')
    c.label('human')
    c.emit('89442428')  # Original arg1; native RET4/RET8 still handles stack.
    absolute('f0ff05', stats)
    c.label('native')
    c.emit('619d')
    c.branch('e9', target)
    return c.finish()
