"""Port the previously tested finite-negative ANT guard onto exact0.7.6 native bytes."""
import hashlib
import struct
import ant_delta_guard_adapter as guard
from pe_adapter import append_adapter
from pe_image_readonly import PE32

BASE='df9f70693dd4167440935725174014d1643c284b05d010fe198681d4b322ace5'
R2='1e5cab30563ef2da390d70d59efdeb95b3796c7560fb19306206b4ce78025339'


def build(base):
    if hashlib.sha256(base).hexdigest() not in (BASE,R2):raise ValueError('Exact DF or R2 client required, no repeat or mixed experiments')
    pe=PE32(base)
    if pe.read(guard.SITE,5)!=guard.ORIGINAL:raise ValueError('Actor update entry changed')
    if pe.read(0xB1496A,5)!=bytes.fromhex('84c07401cc'):raise ValueError('Native negative delta assertion changed')
    eventsync=pe.read(0xE1108E,5)
    new,layout,_,_=append_adapter(base,guard.make_code,b'.qtdtg',b'.qtdts')
    patched=PE32(new)
    offset=patched.offset(guard.SITE,5)
    new[offset:offset+5]=b'\xe9'+struct.pack('<i',layout['adapter']-guard.SITE-5)
    if PE32(new).read(0xB1496A,5)!=pe.read(0xB1496A,5):raise ValueError('Assertion was modified')
    if PE32(new).read(0xE1108E,5)!=eventsync:raise ValueError('EventSync changed')
    return bytes(new),dict(**layout,site=hex(guard.SITE),base_sha256=hashlib.sha256(base).hexdigest(),
        native_assertion_preserved=True,native_eventsync_preserved=True,
        negative_finite_delta_clamped=True,scope='Connected LAN only; all roles/2–4 humans, no player-ID assumptions',
        guest_world_fixed=False,qte_sync_fixed=False,installed=False,published=False,gameplay_verified=False)
