"""Separate opt-in mode0 result getter: first actually finished human among2..4.

No cached IDs, fabricated finish time, success message or position override.
The old two-human adapter remains intact. Native Story predicates decide loss/win.
"""
import struct
from checkpoint_humans_adapter import Code
from team_finish_adapter import SPECS
from team_finish_dynamic_adapter import PLAYER_VTABLE


def make_code(base,stats,target):
    if target not in {native for _,native in SPECS}:raise ValueError('Unsupported getter')
    c=Code(base)
    def absolute(op,value):c.emit(op);c.data+=struct.pack('<I',value)
    c.emit('9c60')
    absolute('a1',0x2888F7C);c.emit('85c0');c.branch('0f84','native')
    c.emit('80780800');c.branch('0f85','native')
    c.emit('83b8a400000003');c.branch('0f85','native')
    absolute('a1',0x28824E8);c.emit('85c0');c.branch('0f84','native')
    c.emit('8b401085c0');c.branch('0f84','native')
    c.emit('8b48f00b48f40b48f80b48fc');c.branch('0f84','native')
    absolute('a1',0x2888F78);c.emit('85c0');c.branch('0f84','native')
    c.emit('8b780883ff02');c.branch('0f82','native')
    c.emit('83ff40');c.branch('0f87','native')
    c.emit('8bb0c000000085f6');c.branch('0f84','native')
    # ESI=table, EDI=capacity, ECX=index, EBX=validated human count.
    c.emit('31c931db')
    c.label('roster')
    c.emit('8b048e85c0');c.branch('0f84','roster_next')
    c.emit('8138');c.data+=struct.pack('<I',PLAYER_VTABLE)
    c.branch('0f85','native')
    c.emit('398834030000');c.branch('0f85','native')
    c.emit('80b86002000001');c.branch('0f84','roster_next')
    c.emit('80b86002000000');c.branch('0f85','native')
    c.emit('4383fb04');c.branch('0f87','native')
    c.label('roster_next');c.emit('4139f9');c.branch('0f82','roster')
    c.emit('83fb02');c.branch('0f82','native')
    # Caller must itself be a validated human, never an NPC/empty/foreign ID.
    c.emit('8b4424283bc7');c.branch('0f83','native')
    c.emit('8b148685d2');c.branch('0f84','native')
    c.emit('80ba6002000000');c.branch('0f85','native')
    # Retain table/capacity while scanning native finish records (ID,float).
    c.emit('89f589fb8b4c24188b71708b797439f7');c.branch('0f86','native')
    c.emit('85f6');c.branch('0f84','native')
    c.emit('89f82bc6a907000000');c.branch('0f85','native')
    c.emit('89f82bc63d00020000');c.branch('0f87','native')
    c.label('finish_record');c.emit('8b0639d8');c.branch('0f83','finish_next')
    c.emit('8b54850085d2');c.branch('0f84','finish_next')
    c.emit('80ba6002000000');c.branch('0f84','human_finish')
    c.label('finish_next');c.emit('83c6083bf7');c.branch('0f82','finish_record')
    c.branch('e9','native')
    c.label('human_finish');c.emit('89442428');absolute('f0ff05',stats)
    c.label('native');c.emit('619d');c.branch('e9',target)
    return c.finish()
