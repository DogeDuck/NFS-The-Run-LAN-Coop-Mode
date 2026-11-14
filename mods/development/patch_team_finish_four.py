"""Append the separate2..4-human result adapter to exactly the frozen0.7.6 client."""
import hashlib
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from team_finish_adapter import SPECS
from team_finish_four_adapter import make_code

BASE='df9f70693dd4167440935725174014d1643c284b05d010fe198681d4b322ace5'
R2='1e5cab30563ef2da390d70d59efdeb95b3796c7560fb19306206b4ce78025339'
R2_DELTA='7d5b68003860aa8af6404e341878544c018e066a3e2f1da820abb9dd07df9d00'


def build(base):
    if hashlib.sha256(base).hexdigest() not in (BASE,R2,R2_DELTA):
        raise ValueError('Exact frozen DF, R2 or R2 finite-delta client required')
    original=PE32(base)
    for site,native in SPECS:
        call=original.read(site,5)
        if call[0]!=0xE8:raise ValueError('Expected existing result getter CALL')
        target=site+5+struct.unpack('<i',call[1:])[0]
        if target==native or not any(s['flags']&0x20000000 and original.base+s['rva']<=target<original.base+s['rva']+s['size'] for s in original.sections):
            raise ValueError('Existing team-result adapter differs')
    def factory(code,stats):
        one=make_code(code,stats,SPECS[0][1])
        if len(one)>1024:raise ValueError('Result adapter overlaps its neighbor')
        return one+b'\xcc'*(1024-len(one))+make_code(code+1024,stats+4,SPECS[1][1])
    data,layout,code,_=append_adapter(base,factory,b'.team4',b'.team4st')
    image=PE32(data)
    for i,(site,_) in enumerate(SPECS):
        offset=image.offset(site,5)
        data[offset:offset+5]=b'\xe8'+struct.pack('<i',layout['adapter']+1024*i-site-5)
    return bytes(data),dict(**layout,humans_min=2,humans_max=4,installed=False,published=False,
        gameplay_verified=False,scope='Native mode0 Story result time/rank only',
        npc_positions_unchanged=True,spawns_extended=False,scripted_qte_finish_fixed=False,
        limitation='Not full4-player support: server start slots and scripted finales still separate.')
