"""Persist the3.5-tested native start-grid/pose mechanism for an explicit race list."""
import json
from pathlib import Path
import struct
import uuid
from pe_adapter import append_adapter
from patch_headless_reset import file_offset,digest
from probe_lifecycle import call_bytes
import story_start_spawn_adapter as a

ROOT=Path(__file__).resolve().parent
BASE='8fa5580076607120edf9e74a24367d74a24988ef7ec172fade15cdff41f2bf6b'


def build(base):
    if digest(base).lower()!=BASE:raise ValueError('Verified paired AI server required')
    catalogue=json.loads((ROOT/'config/story-spawn-stage2-events.json').read_text())
    rows=catalogue['events']
    if catalogue.get('stage1_excluded') is not True or not 1<=len(rows)<=64:
        raise ValueError('Explicit stage2+ catalogue required')
    if any(int(row['event'].split('_')[0])<2 for row in rows):raise ValueError('Intro must remain excluded')
    guids=tuple(uuid.UUID(row['guid']) for row in rows)
    if len(set(guids))!=len(guids) or uuid.UUID(int=0) in guids:raise ValueError('Ambiguous race list')
    sites=((a.SELECT_SITE,call_bytes(a.SELECT_SITE,a.SELECT_NATIVE)),(a.MATRIX_SITE,a.MATRIX_ORIGINAL))
    for site,original in sites:
        offset=file_offset(base,site)
        if base[offset:offset+len(original)]!=original:raise ValueError('Native spawn site changed')
    staged,selection,code1,_=append_adapter(base,lambda code,stats:a.selector_code(code,stats,guids),b'.spngrid',b'.spnstat')
    # The same RW state is shared by both RX adapters. No writable code pages.
    pe=struct.unpack_from('<I',staged,0x3c)[0]
    count=struct.unpack_from('<H',staged,pe+6)[0]
    table=pe+24+struct.unpack_from('<H',staged,pe+20)[0]
    struct.pack_into('<I',staged,table+(count-1)*40+8,80)
    struct.pack_into('<4f',staged,file_offset(staged,selection['counter']+a.OFFSET),8,8,8,0)
    patched,matrix,code2,_=append_adapter(staged,lambda code,unused:a.matrix_code(code,selection['counter'],guids),b'.spnpose',b'.spnaux')
    for (site,original),address,opcode in zip(sites,(selection['adapter'],matrix['adapter']),(b'\xe8',b'\xe9')):
        offset=file_offset(patched,site)
        patched[offset:offset+len(original)]=opcode+struct.pack('<i',address-site-5)+b'\x90'*(len(original)-5)
    return bytes(patched),code1+code2,dict(sha256=digest(patched),selection_layout=selection,matrix_layout=matrix,
        events=rows,stage1_excluded=True,second_human_offset_metres=8,
        gameplay_verified_events=['3_5'],full_campaign_verified=False,
        evidence='User confirmed both cars at race start and driveable in3.5 after full Retry; native selection2/matrix1+1 counters.',
        limitations='Other allowlisted races and the combined disk package have not been tested in game. Garage/pause/team-result changes excluded.')
