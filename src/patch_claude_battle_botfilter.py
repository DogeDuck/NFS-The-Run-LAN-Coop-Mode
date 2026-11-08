"""Isolated bot filter for the EXACT Claude42746E48 client; no HUD/control changes.

The original .btllead treats the whole ClientPlayer vector as human. Live08.11
the vector changed from [0,1] to [0,1,bot2,bot3,bot4] during2.6; current rival3
was consequently accepted as a teammate without a progress comparison.
Redirect only its MOV player-ID instruction. Native bot byte+260!=0 skips this
entry; human entries execute the exact displaced MOV and original logic.
"""
import struct
from checkpoint_humans_adapter import Code
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from patch_headless_reset import digest,file_offset

CLAUDE_SHA='42746e48e5e20fc3ee96c54f30eb0b4d6070d48a966eb9483386aa18db4c309e'
MOV_ID=bytes.fromhex('8b8034030000')


def make_code(base,stats,site,loop):
    c=Code(base);c.emit('9c')
    c.emit('ff05');c.data+=struct.pack('<I',stats)
    c.emit('80b86002000000');c.branch('0f85','bot')
    c.emit('9d');c.data+=MOV_ID;c.branch('e9',site+len(MOV_ID))
    c.label('bot');c.emit('ff05');c.data+=struct.pack('<I',stats+4)
    c.emit('9d');c.branch('e9',loop)
    return c.finish()


def build(base):
    if digest(base)!=CLAUDE_SHA:raise ValueError('Requires exact original Claude v0.7.2 client')
    im=PE32(base)
    if im.read(0xF42020,7)!=bytes.fromhex('8a8160020000c3'):
        raise ValueError('Native bot getter contract changed')
    sec=next(s for s in im.sections if s['name']=='.btllead')
    code=im.read(im.base+sec['rva'],sec['virtual_size'])
    needle=MOV_ID+bytes.fromhex('3b87a8000000')
    if code.count(needle)!=1:raise ValueError('Original player-ID instruction not unique')
    index=code.index(needle)
    prefix=code[index-13:index]
    if prefix[:9]!=bytes.fromhex('8b0683c60485c00f84'):
        raise ValueError('Original player loop contract changed')
    site=im.base+sec['rva']+index
    loop=site+struct.unpack_from('<i',prefix,9)[0]
    if not im.base+sec['rva']<=loop<site or im.read(loop,2)!=bytes.fromhex('39de'):
        raise ValueError('Original player loop destination changed')
    patched,layout,adapter,_=append_adapter(base,lambda address,stats:make_code(address,stats,site,loop),b'.btlbot',b'.btlbots')
    offset=file_offset(patched,site)
    patched[offset:offset+6]=b'\xe9'+struct.pack('<i',layout['adapter']-site-5)+b'\x90'
    return bytes(patched),adapter,dict(base_sha256=digest(base),patched_sha256=digest(patched),
        site=site,loop=loop,layout=layout,gameplay_verified=False,
        stats='PLAYER_ENTRIES+0, SKIPPED_BOTS+4',
        limitations='Only removes bots from original Claude team comparison. No phase/timer/result/control/HUD changes.')
