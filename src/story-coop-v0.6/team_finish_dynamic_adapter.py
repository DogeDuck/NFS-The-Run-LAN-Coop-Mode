"""Candidate permanent mode0 team getters: derive humans from native client table.

No cached event/IDs and no fabricated wins. Both native result getters consult the
first actually finished human. Story result predicates still decide win/loss.
This new dynamic roster variant is offline-tested only, not gameplay validated.
"""
import struct
from binary_helpers import Code
from binary_helpers import SPECS

PLAYER_VTABLE=0x254F020

def make_code(base,stats,target):
    if target not in {n for _,n in SPECS}:raise ValueError('Unsupported getter')
    c=Code(base)
    def absolute(op,a):c.emit(op);c.data+=struct.pack('<I',a)
    def reject():c.branch('0f84','native')
    c.emit('9c60')
    absolute('a1',0x2888F7C);c.emit('85c0');reject()
    c.emit('80780800');c.branch('0f85','native')
    c.emit('83b8a400000003');c.branch('0f85','native')
    absolute('a1',0x28824E8);c.emit('85c0');reject()
    c.emit('8b401085c0');reject()
    # Current asset GUID must be nonzero. Read anew on every getter call.
    c.emit('8b48f00b48f40b48f80b48fc');reject()
    absolute('a1',0x2888F78);c.emit('85c0');reject()
    c.emit('8b780883ff02');c.branch('0f82','native')
    c.emit('83ff40');c.branch('0f87','native')
    c.emit('8bb0c000000085f6');reject()
    # ESI=table, EDI=capacity; ECX=index; EBX=human count; EBP/EDX=IDs.
    c.emit('31c931dbbdffffffffbaffffffff')
    c.label('players')
    c.emit('8b048e85c0');c.branch('0f84','next')
    c.emit('8138');c.data+=struct.pack('<I',PLAYER_VTABLE)
    c.branch('0f85','native')
    c.emit('398834030000');c.branch('0f85','native')
    c.emit('80b86002000001');c.branch('0f84','next')
    c.emit('80b86002000000');c.branch('0f85','native')
    c.emit('83fb00');c.branch('0f85','second')
    c.emit('89cd');c.branch('e9','count')
    c.label('second');c.emit('83fb01');c.branch('0f85','native')
    c.emit('89ca')
    c.label('count');c.emit('43')
    c.label('next');c.emit('4139f9');c.branch('0f82','players')
    c.emit('83fb02');c.branch('0f85','native')
    c.emit('8b44242839e8');c.branch('0f84','order')
    c.emit('39d0');c.branch('0f85','native')
    c.label('order')
    c.emit('8b4c24188b71708b797439f7');c.branch('0f86','native')
    c.emit('85f6');reject()
    c.emit('89f82bc6a907000000');c.branch('0f85','native')
    c.emit('89f82bc63d00020000');c.branch('0f87','native')
    c.label('scan');c.emit('8b0639e8');c.branch('0f84','human')
    c.emit('39d0');c.branch('0f84','human')
    c.emit('83c6083bf7');c.branch('0f82','scan')
    c.branch('e9','native')
    c.label('human');c.emit('89442428');absolute('f0ff05',stats)
    c.label('native');c.emit('619d');c.branch('e9',target)
    return c.finish()
