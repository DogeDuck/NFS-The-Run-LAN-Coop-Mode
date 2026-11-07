"""Prototype: register all human story racers through the native checkpoint initializer.

Two inseparable hooks: widen the first-player predicate and continue native loop
after initialization. No synthetic racer objects or direct record-array writes.
Independent timers remain native; shared co-op checkpoint semantics NOT solved here.
"""
import struct

PREDICATE_SITE = 0x13E734D
CONTINUE_SITE = 0x13E7388
ORIGINAL_PREDICATE = bytes.fromhex('394b107409')
ORIGINAL_CONTINUE = bytes.fromhex('f30f114014')


class Code:
    def __init__(self, base):
        self.base, self.data, self.labels, self.fixups = base, bytearray(), {}, []

    def emit(self, value):
        self.data += bytes.fromhex(value)

    def branch(self, opcode, target):
        self.emit(opcode)
        self.fixups.append((len(self.data), target))
        self.data += bytes(4)

    def label(self, name):
        self.labels[name] = self.base + len(self.data)

    def finish(self):
        for offset, target in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target
            struct.pack_into('<i', self.data, offset, dest - (self.base + offset + 4))
        return bytes(self.data)


def story_guard(code, reject):
    code.emit('a1805c8e0285c0')  # [28E5C80] ServerStoryModeContext
    code.branch('0f84', reject)
    code.emit('8138506d5b02')
    code.branch('0f85', reject)


def make_predicate(base):
    code = Code(base)
    code.emit('394b10')  # Original CMP, same flags for default/native paths.
    code.emit('9c60')
    story_guard(code, 'native')
    # A kind1 story opponent can share the host's player ID. Test driver kind
    # before the original equal-ID fast path, otherwise it masquerades as human.
    code.emit('837b1400')
    code.branch('0f85', 'reject')
    code.emit('8b431083f83f')  # Racer ID from native RacerInfo, bound player table.
    code.branch('0f87', 'reject')
    code.emit('8b1520328a0285d2')
    code.branch('0f84', 'reject')
    code.emit('8b92a400000085d2')  # disp32 +A4, never signed disp8.
    code.branch('0f84', 'reject')
    code.emit('8b148285d2')
    code.branch('0f84', 'reject')
    code.emit('80ba6002000000')  # ServerPlayer bot flag +260, false = human.
    code.branch('0f85', 'reject')
    code.emit('619d39c9')  # Restore regs and present native equal-CMP flags.
    code.branch('e9', 0x13E735B)
    code.label('reject')
    code.emit('619d')
    code.branch('e9', 0x13E7352)
    code.label('native')
    code.emit('619d')
    code.branch('0f84', 0x13E735B)
    code.branch('e9', 0x13E7352)
    return code.finish()


def make_continue(base):
    code = Code(base)
    code.data += ORIGINAL_CONTINUE
    code.emit('9c60')
    story_guard(code, 'native_end')
    code.emit('619d8b442410')  # Native saved RacerInfo end at original ESP+10.
    code.branch('e9', 0x13E7352)  # Advance EDI and loop, no duplicate append.
    code.label('native_end')
    code.emit('619d')
    code.branch('e9', 0x13E738D)
    return code.finish()
