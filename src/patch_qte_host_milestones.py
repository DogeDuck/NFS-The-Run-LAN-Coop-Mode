"""Build exact BCDAFBF8 host milestone candidate; no install or fabricated outcome."""
import hashlib
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
import qte_host_milestones as a

SUPPORTED='bcdafbf8db104fb070e093e147e9e3d440daef15f4499c3a2037313a14bc40aa'


def jump(at,to):return b'\xe9'+struct.pack('<i',to-at-5)


def build(base):
    if hashlib.sha256(base).hexdigest()!=SUPPORTED:raise ValueError('Expected exact BCDAFBF8 RACESTART server')
    p=PE32(base)
    pins={a.HANDLER:a.HEAD,a.RESET:a.RESET_HEAD,a.SUB_SLOT:struct.pack('<I',a.SUB_NATIVE),
          a.PEER_PLAYER:bytes.fromhex('8b8110190000c3'),0x1850800:bytes.fromhex('8b4128c3')}
    for at,data in pins.items():
        if p.read(at,len(data))!=data:raise ValueError('Native contract differs at '+hex(at))
    if p.read(a.HOST_SELECTOR,6)!=bytes.fromhex('e99b33860190'):
        raise ValueError('Installed host selector contract differs')
    if p.read(0x2B8E000,10)!=bytes.fromhex('53565789cebb00f0b802'):
        raise ValueError('Native host selector state differs')
    data,layout,code,_=append_adapter(base,a.make_code,b'.qtehost',b'.qtehst')
    q=PE32(data);entry=layout['adapter']
    for at,value in ((a.HANDLER,jump(a.HANDLER,entry)+b'\x90'*(len(a.HEAD)-5)),
                     (a.RESET,jump(a.RESET,entry+a.RESET_OFFSET)),
                     (a.SUB_SLOT,struct.pack('<I',entry+a.SUB_OFFSET))):
        off=q.offset(at,len(value));data[off:off+len(value)]=value
    pe=struct.unpack_from('<I',data,0x3C)[0];opt=pe+24
    count=struct.unpack_from('<H',data,pe+6)[0];opt_size=struct.unpack_from('<H',data,pe+20)[0]
    struct.pack_into('<I',data,opt+opt_size+(count-1)*40+8,a.STATS_SIZE)
    return bytes(data),dict(**layout,sha256=hashlib.sha256(data).hexdigest(),
        entries=dict(gate=hex(entry),retry=hex(entry+a.RESET_OFFSET),subworld=hex(entry+a.SUB_OFFSET)),
        whitelist=[dict(guid=g,source_group=i) for g,i in a.SYNC_GUIDS],
        scope='Story OOC 10.4 kickandrun.OnStarted / herostealscar.OnFinished, verified named HOST among 2-4 humans',
        host_milestones_only=True,loading_acks_untouched=True,
        no_timeout=True,no_fabricated_ready=True,frame_hook=False,
        host_only_input=False,gameplay_verified=False,installed=False,published=False)
