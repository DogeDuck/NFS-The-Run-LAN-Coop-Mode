"""Experimental: replace a server story bookmark restore with full mission retry.

The adapter runs on the original server thread, clears old bookmark history with
the game's clear function, and invokes the game's restart-message handler.
It falls back to the original restore outside a validated active story context.
All automatic story checkpoint restores use Retry in this experimental build.
"""
from pathlib import Path
import argparse
import datetime
import json
import os
import struct
from patch_headless_reset import require_game_closed,file_offset,digest,patch_bytes

ROOT=Path(__file__).resolve().parent
HOOK=0x13FA023
RESTORE=0x1036920
STORY_GLOBAL=0x28E5C80
STORY_VTABLE=0x25B6D50

def align(value,boundary):return (value+boundary-1)//boundary*boundary

def adapter(address,counter):
    code=bytearray();labels={};fixups=[]
    def emit(hexdata):code.extend(bytes.fromhex(hexdata))
    def absolute(prefix,value):emit(prefix);code.extend(struct.pack('<I',value))
    def call(target):emit('e8');code.extend(struct.pack('<i',target-(address+len(code)+4)))
    def branch(opcode,label):emit(opcode);fixups.append((len(code),label));code.extend(b'\0'*4)
    # Preserve ECX (bookmark manager) on every fallback path.
    absolute('8139',0x25BDA34);branch('0f85','fallback')
    absolute('a1',STORY_GLOBAL);emit('85c0');branch('0f84','fallback')
    absolute('8138',STORY_VTABLE);branch('0f85','fallback')
    emit('83781000');branch('0f84','fallback') # Active challenge required.
    absolute('ff05',counter)
    emit('8b442404');absolute('a3',counter+4) # Requested restore tick.
    # EBP keeps the original stack; ESI and EDI are restored on return.
    emit('558bec565783e4f083ec408bf48bf9')
    emit('6a018bcf');call(0x13FA090) # Clear old history and notify clients.
    emit('8bce');call(0x226A940) # Construct RestartChallengeMessage on aligned stack.
    emit('56');absolute('8b0d',STORY_GLOBAL);call(0x13D0050)
    emit('8bce');call(0x18507E0) # Same base-message destructor used by game senders.
    emit('8b7df88b75fc8be55dc20c00') # Original restore has three stack arguments.
    labels['fallback']=len(code)
    emit('e9');code.extend(struct.pack('<i',RESTORE-(address+len(code)+4)))
    for pos,label in fixups:struct.pack_into('<i',code,pos,labels[label]-pos-4)
    return bytes(code)

def build(base):
    data=bytearray(base)
    pe=struct.unpack_from('<I',data,0x3C)[0]
    count=struct.unpack_from('<H',data,pe+6)[0]
    opt=pe+24;opt_size=struct.unpack_from('<H',data,pe+20)[0]
    assert struct.unpack_from('<H',data,opt)[0]==0x10B,'Expected PE32'
    image_base=struct.unpack_from('<I',data,opt+28)[0]
    assert image_base==0x400000,'Unsupported image base'
    section_align,file_align=struct.unpack_from('<II',data,opt+32)
    assert section_align==0x1000 and file_align in (0x200,0x1000),'Unsupported alignment'
    table=opt+opt_size
    sections=[]
    for i in range(count):
        off=table+i*40
        vs,rva,size,raw=struct.unpack_from('<4I',data,off+8)
        sections.append((rva,vs,size,raw))
    headers=table+count*40
    first_raw=min(raw for rva,vs,size,raw in sections if size)
    if headers+80>first_raw or any(data[headers:headers+80]):raise ValueError('No empty section-header space')
    code_rva=align(max(rva+max(vs,size) for rva,vs,size,raw in sections),section_align)
    stats_rva=code_rva+section_align
    code_va=image_base+code_rva;stats_va=image_base+stats_rva
    code=adapter(code_va,stats_va)
    code_size=align(len(code),file_align);stats_size=file_align
    raw_code=align(len(data),file_align);raw_stats=raw_code+code_size
    assert len(code)<section_align and stats_size<=section_align
    data.extend(b'\0'*(raw_code-len(data)))
    data.extend(code+b'\xcc'*(code_size-len(code)))
    data.extend(b'\0'*stats_size)
    def section(offset,name,virtual_size,rva,size,raw,flags):
        struct.pack_into('<8sIIIIIIHHI',data,offset,name.ljust(8,b'\0'),virtual_size,rva,size,raw,0,0,0,0,flags)
    section(headers,b'.coopfx',len(code),code_rva,code_size,raw_code,0x60000020)
    section(headers+40,b'.coopdt',8,stats_rva,stats_size,raw_stats,0xC0000040)
    struct.pack_into('<H',data,pe+6,count+2)
    struct.pack_into('<I',data,opt+4,struct.unpack_from('<I',data,opt+4)[0]+code_size)
    struct.pack_into('<I',data,opt+8,struct.unpack_from('<I',data,opt+8)[0]+stats_size)
    struct.pack_into('<I',data,opt+56,stats_rva+section_align)
    struct.pack_into('<I',data,opt+64,0) # PE checksum; this is not a driver image.
    site=file_offset(base,HOOK)
    expected=b'\xe8'+struct.pack('<i',RESTORE-HOOK-5)
    if base[site:site+5]!=expected:raise ValueError('Restore call site differs')
    # Validate the original cleanup ABI and all called entry points.
    checks={0x103699B:bytes.fromhex('5ec20c00'),
        0x13FA090:bytes.fromhex('83ec4053'),0x226A940:bytes.fromhex('5668839712b1'),
        0x13D0050:bytes.fromhex('83ec205657'),0x18507E0:None}
    for va,expected_bytes in checks.items():
        if expected_bytes and base[file_offset(base,va):file_offset(base,va)+len(expected_bytes)]!=expected_bytes:
            raise ValueError(f'Called function signature changed: {va:#x}')
    data[site:site+5]=b'\xe8'+struct.pack('<i',code_va-HOOK-5)
    # Existing section content is unchanged apart from the one CALL instruction.
    for rva,vs,size,raw in sections:
        for a,b in ((raw,min(raw+size,site)),(max(raw,site+5),raw+size)):
            if b>a and base[a:b]!=data[a:b]:raise ValueError('Unrelated section content changed')
    info=dict(hook=hex(HOOK),adapter=hex(code_va),counter=hex(stats_va),adapterSize=len(code),
        sectionNames=['.coopfx','.coopdt'],baseHash=digest(base),patchedHash=digest(data),
        scope='Every server bookmark restore while an active story challenge exists becomes a full mission restart')
    return bytes(data),info,code

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',type=Path,default=Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run'))
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    game_dir=args.game_dir.resolve()
    if any(part.casefold()=='therunbackup' for part in game_dir.parts):raise ValueError('User backup excluded')
    original=(ROOT/'backups'/'NFSTR_Server.exe.headless-original').read_bytes()
    base,_=patch_bytes(original)
    patched,info,code=build(base)
    server=game_dir/'NFSTR_Server.exe';current=server.read_bytes()
    if current not in (base,patched):raise ValueError('Unknown server state; restore other experiments first')
    outputs=ROOT/'outputs';outputs.mkdir(exist_ok=True)
    (outputs/'checkpoint-retry-adapter.bin').write_bytes(code)
    if args.check:
        print(json.dumps(dict(status='verified',installed=current==patched,**info),indent=2));return
    replacement=base if args.restore else patched
    if current==replacement:print('Requested checkpoint retry mode is already installed');return
    require_game_closed()
    backup=ROOT/'backups'/'NFSTR_Server.exe.before-checkpoint-retry'
    if backup.exists() and backup.read_bytes()!=base:raise ValueError('Backup differs')
    if not backup.exists():
        with backup.open('xb') as out:out.write(base)
    if backup.read_bytes()!=base:raise RuntimeError('Backup verification failed')
    with server.open('r+b') as out:
        if out.read()!=current:raise RuntimeError('Server changed during preparation')
        out.seek(0);out.write(replacement);out.truncate();out.flush();os.fsync(out.fileno())
    if server.read_bytes()!=replacement:raise RuntimeError('Server verification failed')
    report=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),action='restore' if args.restore else 'patch',
        server=str(server),before=digest(current),after=digest(replacement),**info)
    (outputs/'checkpoint-retry-patch.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
