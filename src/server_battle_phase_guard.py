"""Server: accept each authored BattleStart source/rival once per generation.

Guard13E304F BEFORE writing source+48, actor activation, ranking changes and
NewBattle broadcast. Native enable13E2DD0 clears that source's history; native
global reset13DB700 and challenge changes clear all history. Independent of
sender/player count: any human can trigger the first valid checkpoint,1..4 or
more repeats do not re-activate an old opponent. No client win/result overrides.
"""
import struct
from checkpoint_humans_adapter import Code,story_guard

GATE,RESUME,SKIP=0x13E304F,0x13E3054,0x13E3089
ENABLE,ENABLE_RESUME=0x13E2DD0,0x13E2DD5
RESET,RESET_RESUME=0x13DB700,0x13DB706
GATE_BYTES=bytes.fromhex('8b006a0150')
ENABLE_BYTES=bytes.fromhex('83ec4c5556')
RESET_BYTES=bytes.fromhex('83ec388d0c24')
ENABLE_OFFSET,RESET_OFFSET=0x400,0x600
CACHE,SLOTS,STRIDE=32,24,16
assert CACHE+SLOTS*STRIDE<=512


def absolute(c,op,address):c.emit(op);c.data+=struct.pack('<I',address)


def gate_code(base,stats):
    c=Code(base);c.emit('9c60');absolute(c,'ff05',stats)
    story_guard(c,'native')
    c.emit('8b481085c9');c.branch('0f84','fallback')
    absolute(c,'3b05',stats+16);c.branch('0f85','epoch')
    absolute(c,'3b0d',stats+20);c.branch('0f84','lookup')
    c.label('epoch')
    absolute(c,'a3',stats+16);absolute(c,'890d',stats+20)
    absolute(c,'be',stats+CACHE);c.emit('b918000000')
    c.label('clear')
    c.emit('c7060000000083c61049');c.branch('0f85','clear')
    c.label('lookup')
    # ESI in the original caller is the authored ServerBattleRaceEntity.
    c.emit('8b6c24048b7d148b44241c8b10') # EBP=savedESI; EDI=data; EDX=*savedEAX
    absolute(c,'be',stats+CACHE);c.emit('b91800000031db')
    c.label('entry')
    c.emit('8b0639e8');c.branch('0f85','not_match')
    c.emit('397e04');c.branch('0f85','next')
    c.emit('395608');c.branch('0f84','duplicate');c.branch('e9','next')
    c.label('not_match')
    c.emit('85c0');c.branch('0f85','next')
    c.emit('85db');c.branch('0f85','next');c.emit('89f3')
    c.label('next')
    c.emit('83c61049');c.branch('0f85','entry')
    c.emit('85db');c.branch('0f84','fallback')
    c.emit('892b897b04895308')
    absolute(c,'ff05',stats+24);c.branch('e9','native')
    c.label('duplicate')
    absolute(c,'ff05',stats+4);c.emit('619d');c.branch('e9',SKIP)
    c.label('fallback');absolute(c,'ff05',stats+28)
    c.label('native');c.emit('619d');c.data+=GATE_BYTES;c.branch('e9',RESUME)
    return c.finish()


def clear_code(base,stats,one_source):
    c=Code(base);c.emit('9c60')
    absolute(c,'ff05',stats+(8 if one_source else 12))
    c.emit('89cf') # saved incoming ECX = source entity for Enable
    absolute(c,'be',stats+CACHE);c.emit('b918000000')
    c.label('loop')
    if one_source:
        c.emit('393e');c.branch('0f85','next')
    c.emit('c70600000000')
    c.label('next');c.emit('83c61049');c.branch('0f85','loop')
    c.emit('619d');c.data+=ENABLE_BYTES if one_source else RESET_BYTES
    c.branch('e9',ENABLE_RESUME if one_source else RESET_RESUME)
    return c.finish()


def make_code(base,stats):
    gate=gate_code(base,stats)
    enable=clear_code(base+ENABLE_OFFSET,stats,True)
    reset=clear_code(base+RESET_OFFSET,stats,False)
    if len(gate)>ENABLE_OFFSET or len(enable)>RESET_OFFSET-ENABLE_OFFSET:
        raise ValueError('Server phase adapter overlap')
    return gate+b'\xcc'*(ENABLE_OFFSET-len(gate))+enable+b'\xcc'*(RESET_OFFSET-ENABLE_OFFSET-len(enable))+reset
