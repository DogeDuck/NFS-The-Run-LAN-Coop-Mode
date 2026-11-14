"""LAN-only finite negative ANT step guard; no camera/QTE success override.

Dump18176: B1496E is ANT's deliberate breakpoint for negative ActorController
DeltaT (-0.039554920, caller B151EB). ANT15 explicitly cannot run backwards.
Clamp just this unsupported finite update argument to zero; do not NOP assert.
"""
import struct
from checkpoint_humans_adapter import Code

SITE=0xB1491C
ORIGINAL=bytes.fromhex('f30f10450c')  # movss xmm0,[ebp+C], after native frame setup
ONLINE=0x2888F7C
CALLS,CLAMPED,BYPASSED,NONFINITE,LAST_NEGATIVE=0,4,8,12,16


def make_code(base,stats):
    c=Code(base);c.emit('9c60')
    def absolute(op,address):c.emit(op);c.data+=struct.pack('<I',address)
    absolute('ff05',stats+CALLS)
    absolute('a1',ONLINE);c.emit('85c0');c.branch('0f84','bypass')
    c.emit('80780800');c.branch('0f85','bypass')
    c.emit('83b8a400000003');c.branch('0f85','bypass')
    c.emit('8b450c85c0');c.branch('0f89','native')  # nonnegative sign: exact native
    c.emit('89c225ffffff7f85c0');c.branch('0f84','native')  # preserve negative zero
    c.emit('3d0000807f');c.branch('0f83','nonfinite')  # NaN/Inf remain native
    absolute('8915',stats+LAST_NEGATIVE)
    c.emit('c7450c00000000')  # native per-call stack argument, never scene state
    absolute('ff05',stats+CLAMPED);c.branch('e9','native')
    c.label('nonfinite');absolute('ff05',stats+NONFINITE);c.branch('e9','native')
    c.label('bypass');absolute('ff05',stats+BYPASSED)
    c.label('native');c.emit('619d');c.data+=ORIGINAL;c.branch('e9',SITE+len(ORIGINAL))
    return c.finish()
