"""Ignore duplicate/stale NewBattle START packets for the same battle generation.

Live08.11: server requested opponent2,3,3; the duplicate3 reached both clients
with49.5s left and native990A50 called98C830, counting opponent3 as defeated.
The whole repeated START is ignored, preserving timer, opponent and counter.
Native reset message5B645B2B clears history. Fresh challenge/controller or entity
data identity also starts a new generation. All timer/checkpoint win code stays native.
"""
import struct
from checkpoint_humans_adapter import Code
from coop_hud_adapter import guard

SITE,RESUME=0x990A50,0x990A56
SITE_BYTES=bytes.fromhex('51568bf133d2')
START_MESSAGE,RESET_MESSAGE=0xD71335B4,0x5B645B2B
CACHE=32
SLOTS,CAPACITY,STRIDE=4,24,108
assert CACHE+SLOTS*STRIDE<=512


def absolute(c,op,address):
    c.emit(op);c.data+=struct.pack('<I',address)


def make_code(base,stats):
    c=Code(base);c.emit('9c60')
    # Match native inactive fast path BEFORE dereferencing the packet argument.
    c.emit('80799800');c.branch('0f84','native')
    c.emit('8da974ffffff8b7c2428')       # EBP=Battle(this-8C), EDI=packet
    absolute(c,'ff05',stats)
    c.emit('817f08');c.data+=struct.pack('<I',RESET_MESSAGE);c.branch('0f84','reset')
    guard(c)                          # connected LAN Story only
    c.emit('817f08');c.data+=struct.pack('<I',START_MESSAGE);c.branch('0f85','native')
    c.emit('837f4400');c.branch('0f85','native')  # only START state0, not state1/2
    absolute(c,'a1',0x28824E8);c.emit('85c0');c.branch('0f84','fallback')
    c.emit('8b501085d2');c.branch('0f84','fallback')
    absolute(c,'3b05',stats+16);c.branch('0f85','epoch')
    absolute(c,'3b15',stats+20);c.branch('0f84','lookup')
    c.label('epoch')
    absolute(c,'a3',stats+16);absolute(c,'8915',stats+20)
    absolute(c,'be',stats+CACHE);c.emit('b904000000')
    c.label('clear_epoch')
    c.emit('c70600000000c746080000000083c66c49');c.branch('0f85','clear_epoch')
    c.label('lookup')
    absolute(c,'be',stats+CACHE);c.emit('b90400000031db')
    c.label('slot')
    c.emit('8b0639e8');c.branch('0f84','found')
    c.emit('85c0');c.branch('0f85','next_slot')
    c.emit('85db');c.branch('0f85','next_slot')
    c.emit('89f3')                       # first free slot
    c.label('next_slot')
    c.emit('83c66c49');c.branch('0f85','slot')
    c.emit('85db');c.branch('0f84','fallback')
    c.emit('89de892e')                   # ESI=free; slot.root=EBP
    c.emit('8b4514894604c7460800000000')
    c.label('found')
    c.emit('8b45143b4604');c.branch('0f84','scan')
    c.emit('894604c7460800000000')        # reused root with different entity data
    c.label('scan')
    c.emit('8b4e0883f918');c.branch('0f87','fallback')
    c.emit('8b573c8d5e0c85c9');c.branch('0f84','store')
    c.label('id')
    c.emit('3913');c.branch('0f84','duplicate')
    c.emit('83c30449');c.branch('0f85','id')
    c.label('store')
    c.emit('8b460883f818');c.branch('0f83','saturated')
    c.emit('8954860cff4608');c.branch('e9','native')
    c.label('saturated')
    c.emit('c74608ffffffff');c.branch('e9','fallback')
    c.label('reset')
    absolute(c,'ff05',stats+8)
    absolute(c,'be',stats+CACHE);c.emit('b904000000')
    c.label('reset_slot')
    c.emit('392e');c.branch('0f85','reset_next')
    c.emit('c70600000000c7460800000000')
    c.label('reset_next')
    c.emit('83c66c49');c.branch('0f85','reset_slot')
    c.branch('e9','native')
    c.label('duplicate')
    absolute(c,'ff05',stats+4);c.emit('619dc20400') # exact native RET4 contract
    c.label('fallback');absolute(c,'ff05',stats+12)
    c.label('native');c.emit('619d');c.data+=SITE_BYTES;c.branch('e9',RESUME)
    return c.finish()
