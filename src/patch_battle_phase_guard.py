"""Append an isolated client START-packet guard; no installation or game launch."""
import struct
import battle_phase_guard_adapter as a
from pe_image_readonly import PE32
from pe_adapter import append_adapter
from patch_headless_reset import digest,file_offset

SUPPORTED={'42746e48e5e20fc3ee96c54f30eb0b4d6070d48a966eb9483386aa18db4c309e',
           'fda3873c37a83407a5a863e3cd111c11f0ee804dba4416a9711849fcfa2c48c1'}


def build(base):
    if digest(base) not in SUPPORTED:raise ValueError('Requires Claude client or isolated bot-filter client')
    image=PE32(base)
    if image.read(a.SITE,40)!=bytes.fromhex('51568bf133d23856980f84b90000008b44240c8b480881f9b43513d7743181f92b5b645b0f859e00'):
        raise ValueError('Native Battle message handler changed')
    patched,layout,code,_=append_adapter(base,a.make_code,b'.btlphg',b'.btlphs')
    offset=file_offset(patched,a.SITE)
    patched[offset:offset+6]=b'\xe9'+struct.pack('<i',layout['adapter']-a.SITE-5)+b'\x90'
    return bytes(patched),code,dict(base_sha256=digest(base),patched_sha256=digest(patched),layout=layout,
        gameplay_verified=False,stats='CALLS+0, IGNORED_REPEAT+4, RESETS+8, DECLINED+12',
        source='Repeated NewBattle START, identical or previously seen rival within reset/challenge generation',
        native_win_paths_unchanged=True,server_unchanged=True,
        limitations='Client-side only. Server may still re-activate/restart an NPC before the repeated broadcast; verify that separately. Restart required; do not activate mid-race.')
