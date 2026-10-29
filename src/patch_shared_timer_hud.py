"""Show the existing player-0 story timer in a co-op guest's HUD.

Only mismatched local-player IDs in an active story checkpoint race are routed
to the existing HUD publication block. They skip local countdown decrement and
timeout logic, preserving the original timer's authority.
"""
from pathlib import Path
import argparse
import datetime
import json
import os
import struct
from patch_headless_reset import require_game_closed,file_offset,digest
from patch_manual_road_reset import build as build_manual_reset
from pe_adapter import append_adapter

ROOT=Path(__file__).resolve().parent
HOOK=0x98CF9C
CONTINUE=0x98CFA2
SKIP=0x98D08E
HUD=0x98D064

def adapter(address,counter):
    code=bytearray()
    def emit(value):code.extend(bytes.fromhex(value))
    def absolute(opcode,value):emit(opcode);code.extend(struct.pack('<I',value))
    def branch(opcode,target):emit(opcode);code.extend(struct.pack('<i',target-address-len(code)-4))
    branch('0f84',CONTINUE) # Preserve the original CMP flags for the local timer owner.
    emit('833e00');branch('0f85',SKIP) # Only player-0 shared story timer.
    absolute('a1',0x2882ACC);emit('85c0');branch('0f84',SKIP)
    emit('83b8d000000000');branch('0f86',SKIP) # Existing story-active test.
    absolute('ff05',counter)
    emit('8b4604');absolute('a3',counter+4)
    branch('e9',HUD) # HUD only: bypass decrement and expiration event blocks.
    return bytes(code)

def build(base):
    off=file_offset(base,HOOK)
    expected=b'\x0f\x85'+struct.pack('<i',SKIP-HOOK-6)
    if base[off:off+6]!=expected:raise ValueError('Local-player timer filter differs')
    for va,signature in ((HUD,b'\xe8'+struct.pack('<i',0xE79CA0-HUD-5)),
        (CONTINUE,b'\x8b\xc6\xe8'+struct.pack('<i',0x9894E0-(CONTINUE+2)-5))):
        if base[file_offset(base,va):file_offset(base,va)+len(signature)]!=signature:
            raise ValueError(f'Timer function signature differs: {va:#x}')
    data,layout,code,sections=append_adapter(base,adapter)
    data[off:off+6]=b'\xe9'+struct.pack('<i',layout['adapter']-HOOK-5)+b'\x90'
    for rva,vs,size,raw in sections:
        for a,b in ((raw,min(raw+size,off)),(max(raw,off+6),raw+size)):
            if b>a and base[a:b]!=data[a:b]:raise ValueError('Unrelated section content changed')
    info=dict(hook=hex(HOOK),adapter=hex(layout['adapter']),counter=hex(layout['counter']),adapterSize=len(code),
        baseHash=digest(base),patchedHash=digest(data),scope='Guest HUD publication of existing player-0 story timer; no added countdown or timeout events')
    return bytes(data),info,code

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',type=Path,default=Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run'))
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args();game_dir=args.game_dir.resolve()
    if any(part.casefold()=='therunbackup' for part in game_dir.parts):raise ValueError('User backup excluded')
    original=(ROOT/'backups'/'Need For Speed The Run.exe.lan-before-road-reset').read_bytes()
    base,_=build_manual_reset(original)
    patched,info,code=build(base)
    exe=game_dir/'Need For Speed The Run.exe';current=exe.read_bytes()
    if current not in (base,patched):raise ValueError('Unknown client state')
    outputs=ROOT/'outputs';outputs.mkdir(exist_ok=True)
    (outputs/'shared-timer-hud-adapter.bin').write_bytes(code)
    if args.check:
        print(json.dumps(dict(status='verified',installed=current==patched,**info),indent=2));return
    replacement=base if args.restore else patched
    if current==replacement:print('Requested timer HUD mode already installed');return
    require_game_closed()
    backup=ROOT/'backups'/'Need For Speed The Run.exe.before-shared-timer'
    if backup.exists() and backup.read_bytes()!=base:raise ValueError('Existing backup differs')
    if not backup.exists():
        with backup.open('xb') as out:out.write(base)
    if backup.read_bytes()!=base:raise RuntimeError('Backup verification failed')
    with exe.open('r+b') as out:
        if out.read()!=current:raise RuntimeError('Client changed during preparation')
        out.seek(0);out.write(replacement);out.truncate();out.flush();os.fsync(out.fileno())
    if exe.read_bytes()!=replacement:raise RuntimeError('Client verification failed')
    report=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),action='restore' if args.restore else 'patch',
        executable=str(exe),before=digest(current),after=digest(replacement),**info)
    (outputs/'shared-timer-hud-patch.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
