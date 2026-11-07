"""Persist the Desert Hills-tested AI gate in new server installer deltas."""
import struct
from pe_adapter import append_adapter
from patch_headless_reset import file_offset, digest
from story_ai_gate_adapter import SITE, ORIGINAL, make_code
from story_ai_quota_adapter import SITE as QUOTA_SITE, ORIGINAL as QUOTA_ORIGINAL, make_code as quota_code


def build(base):
    if digest(base).lower() != '22f1604cc40643dbcb18154cda3da627a63f0b34a4dfdfd7631ad99c9a81b768':
        raise ValueError('Verified checkpoint-identity server required')
    offset = file_offset(base, SITE)
    if base[offset:offset+len(ORIGINAL)] != ORIGINAL:
        raise ValueError('AI gate native bytes differ')
    quota_offset = file_offset(base, QUOTA_SITE)
    if base[quota_offset:quota_offset+len(QUOTA_ORIGINAL)] != QUOTA_ORIGINAL:
        raise ValueError('NPC quota native bytes differ')
    def paired_code(address, stats):
        gate = make_code(address, stats, preserve_solo=True)
        if len(gate)>1024:
            raise ValueError('Gate exceeds paired code slot')
        return gate+b'\xcc'*(1024-len(gate))+quota_code(address+1024,stats+64,require_world_flag=False)
    patched, layout, code, _ = append_adapter(base, paired_code, b'.aigate', b'.aigstat')
    patched[offset:offset+len(ORIGINAL)] = b'\xe9'+struct.pack('<i', layout['adapter']-SITE-5)+b'\x90'*(len(ORIGINAL)-5)
    patched[quota_offset:quota_offset+len(QUOTA_ORIGINAL)] = b'\xe9'+struct.pack('<i',layout['adapter']+1024-QUOTA_SITE-5)+b'\x90'*(len(QUOTA_ORIGINAL)-5)
    pe = struct.unpack_from('<I', patched, 0x3c)[0]
    count = struct.unpack_from('<H', patched, pe+6)[0]
    table = pe+24+struct.unpack_from('<H', patched, pe+20)[0]
    struct.pack_into('<I', patched, table+(count-1)*40+8, 128)
    layout.update(quota_adapter=layout['adapter']+1024,quota_counter=layout['counter']+64)
    return bytes(patched), code, dict(layout=layout, sha256=digest(patched),
        gameplay_evidence='Las Vegas event1289338c: two humans plus original two NPCs, user confirmed all present; paired live counters both1',
        limitations='Other missions, scripted police and team finish not verified')
