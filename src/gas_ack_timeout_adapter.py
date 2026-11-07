"""DRAFT experiment, opt-in only: gas station softlock (TANKSTELLE-SPAWNPFAD-2026-11-05-HANDSHAKE.md).

The server level "bundle done?" check 1296E80 (VT 259527C slot +10) returns true only when
[level+7D9]==0 and [level+80C]==0, i.e. every client acked BlueprintBundleClientBundleLoaded/
Unloaded. In LAN the acks never arrive and the load queue blocks forever.

The adapter replaces that vtable slot:
- calls native 1296E80 first; on success it resets the counter and returns true (unchanged);
- blocked only by missing acks ([+7D9]==0, [+80C]!=0): counts consecutive calls; after LIMIT
  it does the native success tail itself (unregisters the 623AD17E listener on +7F8) and
  returns true. [+80C] is NOT written; 12AF450 rebuilds the wait set for the next bundle.
- blocked by [+7D9] or anything else: native false.
SP (acks in ~0.2 s) and normal loads never reach LIMIT. Risk: a client may not have the
bundle when the server continues (invisible car / client error). Live test only with the user.
"""
import struct
from checkpoint_humans_adapter import Code

VTABLE_SLOT = 0x259527C + 0x10
NATIVE = 0x1296E80
LISTENERS = 0x28A31FC
UNREGISTER = 0x4EF070
FAMILY = 0x623AD17E
# RW state layout
FORCED, COUNTER, LAST_80C, CALLS = 0, 4, 8, 12
DEFAULT_LIMIT = 300


def absolute(c, op, address, tail=''):
    c.emit(op)
    c.data += struct.pack('<I', address)
    if tail:
        c.emit(tail)


def adapter_code(base, stats, limit=DEFAULT_LIMIT):
    if not 1 <= limit <= 100000:
        raise ValueError('limit out of range')
    c = Code(base)
    absolute(c, 'ff05', stats + CALLS)                 # inc [CALLS]
    c.emit('51')                                       # push ecx (level)
    c.branch('e8', NATIVE)                             # call native check (thiscall, no args)
    c.emit('59')                                       # pop ecx
    c.emit('84c0')
    c.branch('0f84', 'stuck')
    absolute(c, 'c705', stats + COUNTER, '00000000')   # mov [COUNTER],0
    c.emit('c3')                                       # al=1 from native
    c.label('stuck')
    c.emit('80b9d907000000')                           # cmp byte [ecx+7D9],0
    c.branch('0f85', 'no')
    c.emit('83b90c08000000')                           # cmp dword [ecx+80C],0
    c.branch('0f84', 'no')
    c.emit('8b810c080000')                             # mov eax,[ecx+80C]
    absolute(c, 'a3', stats + LAST_80C)                # mov [LAST_80C],eax
    absolute(c, 'ff05', stats + COUNTER)               # inc [COUNTER]
    absolute(c, '813d', stats + COUNTER)               # cmp [COUNTER],limit
    c.data += struct.pack('<I', limit)
    c.branch('0f82', 'no')
    absolute(c, 'c705', stats + COUNTER, '00000000')
    absolute(c, 'ff05', stats + FORCED)                # inc [FORCED]
    c.emit('56')                                       # push esi
    c.emit('89ce')                                     # mov esi,ecx
    absolute(c, '8b0d', LISTENERS)                     # mov ecx,[28A31FC]
    c.emit('8d86f8070000')                             # lea eax,[esi+7F8]
    c.emit('50')                                       # push eax
    c.emit('68'); c.data += struct.pack('<I', FAMILY)  # push 623AD17E
    c.branch('e8', UNREGISTER)                         # call 4EF070 (callee cleans 8)
    c.emit('5e')                                       # pop esi
    c.emit('b001')                                     # mov al,1
    c.emit('c3')
    c.label('no')
    c.emit('30c0')                                     # xor al,al
    c.emit('c3')
    return c.finish()
