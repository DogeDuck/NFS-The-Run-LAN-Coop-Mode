"""Bounded actor-bus inspection of ALREADY captured minidump memory, no processes."""
import json
from pathlib import Path
import re
import struct
from minidump_memory import DumpMemory, MissingMemory
from qte_spawn_local_bus import SPAWN_VT, BASIC_VT, MAX_PAWNS


def inspect_bytes(data):
    memory=DumpMemory(data); found=set(); candidates=[]; omitted=0
    needle=struct.pack('<I',SPAWN_VT)
    for base,length,offset in memory.ranges:
        if base>=1<<32:continue
        for match in re.finditer(re.escape(needle),data[offset:offset+length]):
            address=base+match.start()
            if address%4 or address in found:continue
            found.add(address)
            if len(found)>256:
                omitted+=1;continue
            row=dict(address=hex(address),status='incomplete captured object')
            candidates.append(row)
            try:
                begin,end,capacity=struct.unpack('<3I',memory.read(address+0x5C,12))
                if begin==0 or end<begin or (end-begin)%4 or end-begin>4*MAX_PAWNS or capacity<end:
                    row['status']='not a bounded initialized spawner';continue
                row.update(native_bus=hex(memory.u32(address+0x6C)),count=(end-begin)//4,pawns=[])
                pointers=struct.unpack('<%dI'%row['count'],memory.read(begin,end-begin))
                for pointer in pointers:
                    pawn=dict(address=hex(pointer),status='not captured');row['pawns'].append(pawn)
                    if not pointer: pawn['status']='null entry';continue
                    try:
                        vt=memory.u32(pointer);pawn['vtable']=hex(vt)
                        if vt!=BASIC_VT:pawn['status']='other type';continue
                        bus=memory.u32(pointer+0x10);player=memory.u32(pointer+0xD8)
                        pawn.update(bus=hex(bus),player=hex(player))
                        pawn['local']=bool(memory.read(player+0x37B,1)[0]&8) if player else False
                        pawn['status']='captured'
                    except MissingMemory:pass
                local=[p for p in row['pawns'] if p.get('status')=='captured' and p.get('local') and p.get('bus')!='0x0']
                row['status']='captured spawner'
                row['local_buses']=[p['bus'] for p in local]
                if len(local)==1:row['native_differs_from_local']=row['native_bus']!=local[0]['bus']
            except MissingMemory:pass
    return dict(captured_ranges=len(memory.ranges),captured_bytes=sum(n for _,n,_ in memory.ranges),
                matches=len(found),omitted=omitted,spawners=candidates,
                warning='Historical captured memory only; stale objects possible. Missing bytes never mean absent objects. A bus mismatch is not proof of the full QTE root cause.')


def summarize(path):
    report=inspect_bytes(path.read_bytes())
    captured=[r for r in report['spawners'] if r['status']=='captured spawner']
    mismatches=[r for r in captured if r.get('native_differs_from_local')]
    out=['QTE spawn dump %s: %d captured ranges, %d bytes, %d VT matches, %d captured spawners'%
         (path.name,report['captured_ranges'],report['captured_bytes'],report['matches'],len(captured))]
    out+=['%s pawns=%s native=%s local=%s mismatch=%s'%(r['address'],r['count'],r['native_bus'],r['local_buses'],r.get('native_differs_from_local','unknown')) for r in captured[:12]]
    out.append('Captured local-bus mismatches: %d; %s'%(len(mismatches),report['warning']))
    return out,report


if __name__=='__main__':
    raise SystemExit('Use coop_summary.py --qte-spawn-dump PATH [--dump-report PATH]')
