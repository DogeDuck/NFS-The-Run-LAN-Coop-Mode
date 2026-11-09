"""Resolve an ObjectBlueprint registry miss by exact EBX bundle membership.

No supplied owner name, no arbitrary root, no sleeps, no fake registry node.
Only a unique registered bundle owner is accepted; ambiguous/missing stays native.
ordered=True (09.11. 22:10, guest crash end of 10.5 with sec2+sec3 registered): owners are a priority list
(index 0 = best); several registered owners -> the best rank wins (PRIORITY counter). Equal rank on two
different nodes stays ambiguous/native. ordered=False is byte-identical to the previous behaviour.
GUID at DatabasePartition+C matches both saved client captures of the prefab.
All scratch search state is on the calling thread's stack.
"""
import struct,uuid
from checkpoint_humans_adapter import Code

SITE,TARGET,LOOKUP,HANDLE_TABLE=0x45AEB2,0x44CFF0,0x440030,0x2714B30
OWNER_VT,PARTITION_VT=0x23E2860,0x23EE0C4
CALLS,FALLBACKS,DECLINED,AMBIGUOUS,VISITS,FOUND,OVERFLOW,PRIORITY=0,4,8,12,16,20,24,28
STATS_SIZE=32

def make_code(base,stats,asset_guid,owner_guids,lookup=LOOKUP,ordered=False):
    if ordered:owners=list(dict.fromkeys(uuid.UUID(g).bytes_le for g in owner_guids))
    else:owners=sorted({uuid.UUID(g).bytes_le for g in owner_guids})
    if not 1<=len(owners)<=32:raise ValueError('Use1..32 unique bundle owners')
    prefab=uuid.UUID(asset_guid).bytes_le
    c=Code(base)
    def absolute(op,address):c.emit(op);c.data+=struct.pack('<I',address)
    def count(offset):absolute('f0ff05',stats+offset)
    def compare_guid(register,data,label):
        # register EAX or EDX; first three fields are little endian as native EBX.
        modrm='78' if register=='eax' else '7a'
        for off,value in zip((12,16,20,24),struct.unpack('<4I',data)):
            c.emit('81'+modrm+format(off,'02x'));c.data+=struct.pack('<I',value);c.branch('0f85',label)
    # Native rb-find runs16 bytes below original entry; save map above its copied args.
    c.emit('8d6424fc890c24ff74240cff74240c');c.branch('e8',TARGET)
    c.emit('9c6081ec00020000')  # native registers/flags, then512 bytes local workspace
    count(CALLS)
    absolute('a1',0x2888F7C);c.emit('85c0');c.branch('0f84','done')
    c.emit('80780800');c.branch('0f85','done')
    c.emit('83b8a400000003');c.branch('0f85','done')
    c.emit('8b9c24240200008bb4242c0200008b06') # EBX=saved map, ESI=out
    c.emit('8d530439d0');c.branch('0f85','done')
    c.emit('8b8424300200008b0085c0');c.branch('0f84','decline') # key slot
    c.emit('813840073e02');c.branch('0f85','decline')  # ObjectBlueprint
    c.emit('8b8424000200008b400c85c0');c.branch('0f84','decline') # original EDI/parent handle
    c.emit('50');absolute('b9',HANDLE_TABLE);c.branch('e8',lookup)
    c.emit('85c0');c.branch('0f84','decline')
    c.emit('813850e25602');c.branch('0f85','decline')  # verified parent reference type
    c.emit('8b500485d2');c.branch('0f84','decline')
    c.emit('813a');c.data+=struct.pack('<I',PARTITION_VT);c.branch('0f85','decline')
    compare_guid('edx',prefab,'decline')
    c.emit('8d7c242031edc70424000000008b430c83e0fe8907b901000000') # stack/root, visits, candidate
    if ordered:c.emit('c7442404ffffffff')  # best rank so far
    c.label('loop');c.emit('85c9');c.branch('0f84','finish')
    c.emit('498b148f85d2');c.branch('0f84','loop')
    c.emit('8d430439c2');c.branch('0f84','loop')
    c.emit('ff0424813c2480000000');c.branch('0f87','overflow')
    count(VISITS)
    c.emit('8b420c85c0');c.branch('0f84','children')
    c.emit('8138');c.data+=struct.pack('<I',0x23E3BA0);c.branch('0f85','children')
    c.emit('8b400485c0');c.branch('0f84','children')
    c.emit('8138');c.data+=struct.pack('<I',PARTITION_VT);c.branch('0f85','children')
    for i,guid in enumerate(owners):
        compare_guid('eax',guid,'owner_next_'+str(i))
        if ordered:c.emit('c7442408');c.data+=struct.pack('<I',i)  # rank of this owner
        c.branch('e9','match');c.label('owner_next_'+str(i))
    c.branch('e9','children')
    c.label('match');c.emit('8b421085c0');c.branch('0f84','decline')
    c.emit('8138');c.data+=struct.pack('<I',OWNER_VT);c.branch('0f85','decline')
    c.emit('85ed');c.branch('0f84','remember')
    if ordered:
        c.emit('39d5');c.branch('0f84','children')            # same node again
        c.emit('8b4424083b442404');c.branch('0f82','better');c.branch('0f87','children')
        c.branch('e9','ambiguous')                            # equal rank, other node
        c.label('better');count(PRIORITY);c.emit('89d58944240'+'4');c.branch('e9','children')
        c.label('remember');c.emit('89d58b4424088944240'+'4')
    else:
        c.emit('39d5');c.branch('0f85','ambiguous');c.branch('e9','children')
        c.label('remember');c.emit('89d5')
    c.label('children');c.emit('83f93e');c.branch('0f87','overflow')
    c.emit('8b0289048f418b420489048f41');c.branch('e9','loop')
    c.label('finish');c.emit('85ed');c.branch('0f84','decline')
    c.emit('892e');absolute('892d',stats+FOUND);count(FALLBACKS);c.branch('e9','done')
    c.label('ambiguous');count(AMBIGUOUS);c.branch('e9','decline')
    c.label('overflow');count(OVERFLOW)
    c.label('decline');count(DECLINED)
    c.label('done');c.emit('81c400020000619d8d642404c20800')
    return c.finish()
