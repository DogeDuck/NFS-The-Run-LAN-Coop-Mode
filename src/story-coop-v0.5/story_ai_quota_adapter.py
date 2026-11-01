"""Experimental Story fill-quota candidate, never deployed automatically.

Preserve the native solo filler count for exactly two humans only if the current
native start-grid bitmap has enough free slots. Authored police/actor spawns are
separate. Does not change global world flags, teams, vehicles or total settings.
"""
import struct
from checkpoint_humans_adapter import Code,story_guard

SITE=0x13D6566
ORIGINAL=bytes.fromhex('8b83c80500002b44241c')

def make_code(base,stats,require_world_flag=True):
    c=Code(base)
    def absolute(op,value):c.emit(op);c.data+=struct.pack('<I',value)
    c.emit('9c60')
    story_guard(c,'native')
    # PUSHFD/PUSHAD add36 bytes: native local human count+1C becomes+40.
    c.emit('837c244002');c.branch('0f85','native')
    # Repeat native enable guards; never turn AI on in an event which disabled it.
    if require_world_flag:
        absolute('a1',0x28A3228);c.emit('85c0');c.branch('0f84','native')
        c.emit('80b8031a000000');c.branch('0f84','native')
    c.emit('80bbc305000000');c.branch('0f84','native')
    c.emit('8b83c805000083f802');c.branch('0f82','no_fill')
    c.emit('83f810');c.branch('0f87','native')
    c.emit('8bd048') # EDX native total; EAX required AI=total-1.
    absolute('a3',stats+12)
    # Verified caller-local RaceSettings pointer: original ESP+28 -> saved ESP+4C.
    c.emit('8b7c244c85ff');c.branch('0f84','native')
    c.emit('8b4f288b772485f6');c.branch('0f84','native')
    c.emit('39f1');c.branch('0f82','native')
    c.emit('2bce');c.emit('f6c103');c.branch('0f85','native')
    c.emit('c1e90283f940');c.branch('0f87','native')
    c.emit('42');c.emit('3bca');c.branch('0f82','native') # grid capacity >= nativeTotal+1
    c.emit('8b7f4885ff');c.branch('0f84','native')
    # BT indexes the native dword bitmap; count free slots, bounded to64.
    c.emit('31f631d2')
    c.label('bit_loop')
    c.emit('0fa337');c.branch('0f82','occupied')
    c.emit('42')
    c.label('occupied');c.emit('463bf1');c.branch('0f82','bit_loop')
    c.emit('3bd0');c.branch('0f82','native') # available slots must cover all intended AI.
    absolute('ff05',stats)
    c.emit('619d8b83c805000083e801');c.branch('e9',SITE+len(ORIGINAL))
    c.label('no_fill')
    # Native unsigned total-human subtraction can underflow when two humans join
    # a one-slot event. Zero intended solo fillers, do not loop0xFFFFFFFF times.
    absolute('ff05',stats);absolute('ff05',stats+8)
    c.emit('619d31c0');c.branch('e9',SITE+len(ORIGINAL))
    c.label('native');absolute('ff05',stats+4)
    c.emit('619d');c.data+=ORIGINAL;c.branch('e9',SITE+len(ORIGINAL))
    return c.finish()
