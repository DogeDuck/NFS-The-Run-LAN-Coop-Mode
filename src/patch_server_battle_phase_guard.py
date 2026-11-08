"""Build-only server guard on the original Claude B912B57B baseline."""
import struct
import server_battle_phase_guard as a
from pe_image_readonly import PE32
from pe_adapter import append_adapter
from patch_headless_reset import digest,file_offset

BASE_SHA='b912b57bf013dc6ac37c2bc0dae8367496776ed5429f7afce6b319015ae8512c'


def build(base):
    if digest(base)!=BASE_SHA:raise ValueError('Requires original Claude B912B57B server')
    image=PE32(base)
    specs=((a.GATE,a.GATE_BYTES,0),(a.ENABLE,a.ENABLE_BYTES,a.ENABLE_OFFSET),(a.RESET,a.RESET_BYTES,a.RESET_OFFSET))
    for site,expected,_ in specs:
        if image.read(site,len(expected))!=expected:raise ValueError('Server phase native contract changed')
    patched,layout,code,_=append_adapter(base,a.make_code,b'.svbphg',b'.svbphs')
    for site,expected,offset in specs:
        raw=file_offset(patched,site)
        patched[raw:raw+len(expected)]=b'\xe9'+struct.pack('<i',layout['adapter']+offset-site-5)+b'\x90'*(len(expected)-5)
    return bytes(patched),code,dict(base_sha256=digest(base),patched_sha256=digest(patched),layout=layout,
        gameplay_verified=False,player_count_independent=True,
        guard_before_actor_activation=True,native_win_paths_unchanged=True,
        stats='CALLS+0, IGNORED_REPEAT+4, ENABLE_RESET+8, GLOBAL_RESET+12, ACCEPTED+24, DECLINED+28',
        limitations='Bounded24 authored source/rival pairs per challenge, native fallback if full; verify enable/reset and legitimate repeated rivals in game.')
